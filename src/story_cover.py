import re, urllib.parse, requests, json
from bs4 import BeautifulSoup
from typing import Optional, Tuple, Dict, Any
from paths import PATHS
import time
import os



HDRS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}
SIZE_RE = re.compile(r"(/books/\d+)([sml])(/[^/?#]+\.(?:jpe?g|png|webp))", re.I)


# --- Literary awards (robust DOM + Next.js fallback) ---

# --- Awards as a list[str] ---

def _dedupe_preserve_case(seq: list[str]) -> list[str]:
    seen, out = set(), []
    for s in seq:
        k = s.strip().lower()
        if k and k not in seen:
            seen.add(k); out.append(s.strip())
    return out

def _extract_awards_dom(soup: BeautifulSoup) -> list[str]:
    names = []
    for a in soup.select('span[data-testid="award"] a'):
        txt = " ".join(a.stripped_strings)              # merge multi-line text
        txt = txt.replace("“","").replace("”","").replace('"',"").strip()
        txt = re.sub(r"\s*\(\d{4}\)\s*", "", txt)       # drop any (YYYY)
        if txt:
            names.append(txt)
    return _dedupe_preserve_case(names)

def _extract_awards_next(soup: BeautifulSoup) -> list[str]:
    tag = soup.find("script", id="__NEXT_DATA__", attrs={"type":"application/json"})
    if not tag or not tag.string:
        return []
    try:
        data = json.loads(tag.string)
    except Exception:
        return []

    found: list[str] = []
    def add(v: Optional[str]):
        v = (v or "").strip()
        if v: found.append(v)

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if re.search(r"award", k, re.I) and isinstance(v, list):
                    for it in v:
                        if isinstance(it, dict):
                            add(it.get("name") or it.get("awardName") or it.get("title"))
                        elif isinstance(it, str):
                            add(it)
                else:
                    walk(v)
        elif isinstance(node, list):
            for it in node: walk(it)

    walk(data)
    return _dedupe_preserve_case(found)


# ---------- Genres ----------
def _uniq_by_name(dicts):
    seen = set(); out = []
    for d in dicts:
        nm = (d.get("name") or "").strip()
        if not nm: 
            continue
        k = nm.lower()
        if k in seen: 
            continue
        seen.add(k); out.append(d)
    return out

def _extract_genres_dom(soup: BeautifulSoup) -> list[dict]:
    """Reads the 'Top genres for this book' chips."""
    genres = []
    for a in soup.select('[data-testid="genresList"] a[href*="/genres/"]'):
        name = a.get_text(strip=True)
        href = a.get("href")
        url  = urllib.parse.urljoin("https://www.goodreads.com", href) if href else None
        slug = None
        if href:
            m = re.search(r"/genres/([\w-]+)", href)
            if m: slug = m.group(1)
        if name:
            rec = {"name": name}
            if slug: rec["slug"] = slug
            if url:  rec["url"]  = url
            genres.append(rec)
    return _uniq_by_name(genres)

def _extract_genres_next(soup: BeautifulSoup) -> list[dict]:
    """Fallback to Next.js boot payload (__NEXT_DATA__)."""
    tag = soup.find("script", id="__NEXT_DATA__", attrs={"type": "application/json"})
    if not tag or not tag.string:
        return []
    try:
        data = json.loads(tag.string)
    except Exception:
        return []

    found = []
    def add(name=None, slug=None, url=None):
        name = (name or "").strip()
        if not name: return
        rec = {"name": name}
        if slug: rec["slug"] = slug
        if url:  rec["url"]  = url
        found.append(rec)

    def walk(node):
        if isinstance(node, dict):
            # Common shapes seen in Goodreads payloads
            for key in ("genres", "topGenres"):
                if key in node and isinstance(node[key], list):
                    for it in node[key]:
                        if isinstance(it, dict):
                            add(it.get("name") or it.get("genreName"),
                                it.get("slug"),
                                it.get("url") or it.get("webUrl"))
                        elif isinstance(it, str):
                            add(it)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(data)
    return _uniq_by_name(found)

def _extract_genres(soup: BeautifulSoup, names_only: bool = True):
    genres = _extract_genres_dom(soup)
    if not genres:
        genres = _extract_genres_next(soup)
    if names_only:
        return [g["name"] for g in genres]
    return genres


# ---- utils ----
def _uniq(seq):
    seen = set(); out = []
    for x in seq:
        if not x: continue
        key = json.dumps(x, sort_keys=True) if isinstance(x, dict) else str(x)
        if key in seen: continue
        seen.add(key); out.append(x)
    return out

def _get_dd_by_label(soup: BeautifulSoup, label: str) -> Optional[BeautifulSoup]:
    dt = soup.find(lambda t: t.name == "dt" and t.get_text(strip=True).lower() == label.lower())
    return _following_dd(dt)

def _parse_awards_dd(dd) -> list:
    """Extract awards like:
       <span data-testid="award"><a>Pulitzer Prize for Fiction (1953)</a></span>, ...
    """
    def strip_quotes(s: str) -> str:
        return s.replace("“","").replace("”","").replace('"',"").strip()

    items = []

    # Preferred: grab each award anchor; its text usually contains the year in parentheses.
    for sp in dd.select("[data-testid='award']"):
        a = sp.find("a")
        if not a: 
            continue
        txt = strip_quotes(a.get_text(" ", strip=True))
        # e.g. "Pulitzer Prize for Fiction (1953)"
        m = re.search(r"\((\d{4})\)", txt)             # not anchored to end anymore
        year = int(m.group(1)) if m else None
        name = re.sub(r"\s*\(\d{4}\)\s*", "", txt).strip()
        href = a.get("href")
        url = urllib.parse.urljoin("https://www.goodreads.com", href) if href else None

        if name:
            rec = {"name": name}
            if year: rec["year"] = year
            if url:  rec["url"] = url
            items.append(rec)

    if items:
        # de-dupe while preserving order
        seen, out = set(), []
        for it in items:
            key = (it["name"], it.get("year"), it.get("url"))
            if key in seen: 
                continue
            seen.add(key); out.append(it)
        return out

    # Fallback: parse visible text (commas between awards; keep years inside parentheses)
    raw = strip_quotes(" ".join(dd.stripped_strings))
    parts = re.split(r"\s*,\s*(?![^()]*\))", raw)  # split on commas not inside (...)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        m = re.search(r"\((\d{4})\)", p)
        year = int(m.group(1)) if m else None
        name = re.sub(r"\s*\(\d{4}\)\s*", "", p).strip()
        if name:
            items.append({"name": name, **({"year": year} if year else {})})

    return items


def _parse_links_or_csv(dd) -> list:
    vals = [a.get_text(strip=True) for a in dd.select("a") if a.get_text(strip=True)]
    if not vals:
        raw = dd.get_text(" ", strip=True)
        vals = [v.strip() for v in re.split(r"\s*,\s*|\s+and\s+", raw) if v.strip()]
    return _uniq(vals)




def _extract_work_details(soup: BeautifulSoup) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    awards = _extract_awards_dom(soup) or _extract_awards_next(soup)
    if awards:
        out["awards"] = awards

    # settings / characters (DOM first, Next.js to fill gaps)
    nxt = _extract_work_details_next(soup)
    s_dom = _parse_links_or_csv(_get_dd_by_label(soup, "Setting")) or []
    c_dom = _parse_links_or_csv(_get_dd_by_label(soup, "Characters")) or []
    if s_dom or nxt.get("setting"):     out["setting"] = s_dom or nxt.get("setting")
    if c_dom or nxt.get("characters"):  out["characters"] = c_dom or nxt.get("characters")

    return out



def _extract_from_next_data(soup: BeautifulSoup) -> Dict[str, str]:
    """Parse Next.js boot JSON for edition identifiers."""
    tag = soup.find("script", id="__NEXT_DATA__", attrs={"type": "application/json"})
    if not tag or not tag.string:
        return {}
    try:
        data = json.loads(tag.string)
    except Exception:
        return {}

    found: Dict[str, str] = {}

    def norm_isbn13(v: str) -> Optional[str]:
        raw = re.sub(r"\D", "", str(v))
        return raw if len(raw) == 13 else None

    def norm_isbn10(v: str) -> Optional[str]:
        raw = re.sub(r"[^0-9Xx]", "", str(v)).upper()
        return raw if re.fullmatch(r"\d{9}[0-9X]", raw) else None

    def norm_asin(v: str) -> Optional[str]:
        raw = re.sub(r"[^A-Za-z0-9]", "", str(v)).upper()
        m = re.search(r"[A-Z0-9]{10}", raw)
        return m.group(0) if m else None

    def walk(node):
        if isinstance(node, dict):
            # common keys seen in Goodreads Next data
            for key in ("isbn", "isbn13", "isbn_13"):
                if key in node and "isbn13" not in found:
                    v = norm_isbn13(node[key])
                    if v: found["isbn13"] = v
            for key in ("isbn10", "isbn_10"):
                if key in node and "isbn10" not in found:
                    v = norm_isbn10(node[key])
                    if v: found["isbn10"] = v
            for key in ("asin", "ebookAsin", "ebook_asin", "kindleAsin", "kindle_asin"):
                if key in node and "asin" not in found:
                    v = norm_asin(node[key])
                    if v: found["asin"] = v
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(data)
    return found


def _size_variant(url: str, size: str) -> str:
    m = SIZE_RE.search(url)
    if not m or size.lower() not in {"s","m","l"}: return url
    prefix = url[: m.start(1)]
    books_part, _, tail = m.groups()
    return f"{prefix}{books_part}{size.lower()}{tail}"

def _fetch_img(url: str) -> Optional[bytes]:
    r = requests.get(url, headers=HDRS, timeout=20)
    return r.content if r.ok and r.headers.get("content-type","").startswith("image/") else None

def _extract_ids_from_url(url: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    m = re.search(r"/book/show/(\d+)", url)
    if m:
        out["goodreads_book_id"] = m.group(1)
    mw = re.search(r"/work(?:/(?:show|editions))?/(\d+)", url)
    if mw:
        out["goodreads_work_id"] = mw.group(1)
    return out


def _extract_ids_from_dom(soup: BeautifulSoup) -> Dict[str, str]:
    out: Dict[str, str] = {}
    # canonical or og:url often carry the clean /book/show/<id> URL
    canon = soup.find("link", rel="canonical")
    if canon and canon.get("href"):
        out.update(_extract_ids_from_url(canon["href"]))
        out.setdefault("canonical_url", canon["href"])
    og_url = soup.find("meta", attrs={"property": "og:url"})
    if og_url and og_url.get("content"):
        out.update(_extract_ids_from_url(og_url["content"]))
        out.setdefault("canonical_url", og_url["content"])
    # look for any link to a work page to grab work_id
    work_a = soup.select_one("a[href*='/work/']")
    if work_a and work_a.get("href"):
        out.update(_extract_ids_from_url(urllib.parse.urljoin("https://www.goodreads.com", work_a["href"])))
    return out


def _extract_work_details_next(soup: BeautifulSoup) -> Dict[str, Any]:
    tag = soup.find("script", id="__NEXT_DATA__", attrs={"type": "application/json"})
    if not tag or not tag.string:
        return {}
    try:
        data = json.loads(tag.string)
    except Exception:
        return {}

    awards, settings, characters = [], [], []

    def add_award(name, year=None, url=None):
        name = (name or "").strip()
        if not name: return
        rec = {"name": name}
        if isinstance(year, int): rec["year"] = year
        if url: rec["url"] = url
        awards.append(rec)

    def visit(node, path=""):
        if isinstance(node, dict):
            # Awards
            if "awards" in node and isinstance(node["awards"], list):
                for it in node["awards"]:
                    if isinstance(it, dict):
                        add_award(it.get("name") or it.get("awardName") or it.get("title"),
                                  it.get("year") or it.get("yearAwarded"),
                                  it.get("url"))
            if "literaryAwards" in node and isinstance(node["literaryAwards"], list):
                for it in node["literaryAwards"]:
                    if isinstance(it, dict):
                        add_award(it.get("name") or it.get("awardName") or it.get("title"),
                                  it.get("year") or it.get("yearAwarded"),
                                  it.get("url"))

            # Settings / places
            for k in ("settings", "places", "settingPlaces"):
                if k in node and isinstance(node[k], list):
                    for it in node[k]:
                        if isinstance(it, dict):
                            nm = it.get("name") or it.get("placeName")
                            if nm: settings.append(nm.strip())
                        elif isinstance(it, str):
                            settings.append(it.strip())

            # Characters
            if "characters" in node and isinstance(node["characters"], list):
                for it in node["characters"]:
                    if isinstance(it, dict):
                        nm = it.get("name") or it.get("characterName")
                        if nm: characters.append(nm.strip())
                    elif isinstance(it, str):
                        characters.append(it.strip())

            for v in node.values():
                visit(v, path)
        elif isinstance(node, list):
            for v in node:
                visit(v, path)

    visit(data)

    out: Dict[str, Any] = {}
    if awards:    out["awards"] = _uniq(awards)
    if settings:  out["setting"] = _uniq(settings)
    if characters: out["characters"] = _uniq(characters)
    return out


def _extract_work_details(soup: BeautifulSoup) -> Dict[str, Any]:
    out: Dict[str, Any] = {}

    # Awards = list[str]
    awards = _extract_awards_dom(soup) or _extract_awards_next(soup)
    if awards:
        out["awards"] = _dedupe_preserve_case(awards)

    # Settings/Characters: DOM first
    dd_setting = _get_dd_by_label(soup, "Setting")
    dom_setting = _parse_links_or_csv(dd_setting) if dd_setting else []

    dd_chars = _get_dd_by_label(soup, "Characters")
    dom_chars = _parse_links_or_csv(dd_chars) if dd_chars else []

    # Fill gaps from Next.js boot JSON
    nxt = _extract_work_details_next(soup)  # returns {"setting": [...], "characters": [...]} if present
    setting = dom_setting or nxt.get("setting", [])
    characters = dom_chars or nxt.get("characters", [])

    if setting:    out["setting"] = setting
    if characters: out["characters"] = characters
    return out


# --- add near top with your other regexes ---
ISBN13_RE = re.compile(r"\b97[89][\d\-]{10,16}\b")
ISBN10_RE = re.compile(r"\b\d{9}[\dXx]\b")
ASIN_RE   = re.compile(r"\bB0[A-Z0-9]{8}\b", re.I)  # Kindle-style ASIN; some pages reuse ISBN10

def _following_dd(dt):
    """Goodreads uses <dt>ISBN</dt><dd>...</dd> pairs inside .DescListItem."""
    if not dt: return None
    dd = dt.find_next_sibling("dd")
    if dd: return dd
    # some pages wrap dt+dd in a div; grab the dd inside that wrapper
    if dt.parent and dt.parent.name != "dl":
        dd = dt.parent.find("dd")
    return dd

def _extract_isbn_asin(soup: BeautifulSoup) -> Dict[str, str]:
    out: Dict[str, str] = {}

    # --- 1) Try DOM (works if server-rendered) ---
    dt_isbn = soup.find(lambda t: t.name == "dt" and t.get_text(strip=True).lower() == "isbn")
    dd_isbn = _following_dd(dt_isbn)
    if dd_isbn:
        text = dd_isbn.get_text(" ", strip=True)
        m13 = ISBN13_RE.search(text)
        if m13: out["isbn13"] = re.sub(r"\D", "", m13.group(0))
        m10 = ISBN10_RE.search(text)
        if m10: out["isbn10"] = m10.group(0).upper()

    asin_span = soup.select_one("[data-testid='asin']")
    if asin_span:
        raw = asin_span.get_text(strip=True).upper()
        if re.fullmatch(r"[A-Z0-9]{10}", raw):
            out["asin"] = raw
    else:
        dt_asin = soup.find(lambda t: t.name == "dt" and t.get_text(strip=True).lower() == "asin")
        dd_asin = _following_dd(dt_asin)
        if dd_asin:
            t = dd_asin.get_text(" ", strip=True)
            m = ASIN_RE.search(t) or ISBN10_RE.search(t)
            if m: out["asin"] = m.group(0).upper()

    # --- 2) Next.js boot JSON (works when DOM is empty) ---
    if not {"isbn13","isbn10","asin"} & out.keys():
        out.update({k:v for k,v in _extract_from_next_data(soup).items() if k not in out})

    # --- 3) JSON-LD fallback ---
    if "isbn13" not in out or "isbn10" not in out:
        for tag in soup.select('script[type="application/ld+json"]'):
            if not tag.string: continue
            try:
                payload = json.loads(tag.string)
            except Exception:
                continue
            def find_isbn(node):
                if isinstance(node, dict):
                    if "isbn" in node: return node["isbn"]
                    for v in node.values():
                        r = find_isbn(v)
                        if r: return r
                elif isinstance(node, list):
                    for it in node:
                        r = find_isbn(it)
                        if r: return r
                return None
            val = find_isbn(payload)
            if not val: continue
            vals = val if isinstance(val, list) else [val]
            for v in vals:
                raw = re.sub(r"[^0-9Xx]", "", str(v))
                if len(raw) == 13 and "isbn13" not in out: out["isbn13"] = raw
                elif len(raw) == 10 and "isbn10" not in out: out["isbn10"] = raw.upper()
            if "isbn13" in out and "isbn10" in out: break

    return out


def fetch_goodreads_cover_by_title(title: str, size: str = "l") -> Optional[Dict[str, Any]]:
   
    # 1) search
    q = urllib.parse.urlencode({"q": title.strip()})
    search_url = f"https://www.goodreads.com/search?{q}"
    sr = requests.get(search_url, headers=HDRS, timeout=20)
    if sr.status_code != 200:
        return None
    soup = BeautifulSoup(sr.text, "html.parser")
    row = soup.select_one("table.tableList tr")
    if not row: return None
    href_el = row.select_one("a.bookTitle")
    if not href_el or not href_el.get("href"):
        return None
    book_url = urllib.parse.urljoin("https://www.goodreads.com", href_el["href"])

    # 2) book page → og:image + ids + fields
    br = requests.get(book_url, headers=HDRS, timeout=25)
    if br.status_code != 200:
        return None
    bs = BeautifulSoup(br.text, "html.parser")

    # image
    og = bs.find("meta", attrs={"property": "og:image"})
    img_url = og.get("content") if og else None
    if not img_url:
        img = bs.select_one("#coverImage")
        if img and img.get("src"): img_url = img["src"]
    if not img_url or "nophoto/book" in img_url:
        return None
    img_url = urllib.parse.urljoin("https://www.goodreads.com", img_url)
    try_url = _size_variant(img_url, size)
    
    cover_bytes = _fetch_img(try_url)
    if cover_bytes:
        cover_url_used = try_url
    else:
        cover_bytes = _fetch_img(img_url)
        cover_url_used = img_url

    if not cover_bytes:
        return None
    



    genres = _extract_genres(bs)

    # ids + metadata
    data: Dict[str, Any] = {
        "cover_url_used": cover_url_used,
        "cover_bytes": cover_bytes,
        "page_url": book_url,
    }

    data.update(_extract_ids_from_url(book_url))
    data.update(_extract_ids_from_dom(bs))


    ids = _extract_isbn_asin(bs)
    if ids:
        data.update(ids)                  # e.g., isbn13 / isbn10 / asin at top-level
        data.setdefault("edition", {}).update(ids)  # also nested if you prefer grouping
    
    # work_details = _extract_work_details(bs)
    # if work_details:
    #     data.setdefault("work_details", {}).update(work_details)

    # genres (top-level list of names)
    
    # if genres:
    #     data["genres"] = genres

    return data


#story_book_cover
#story_metadata
#st

# --- Example ---

#function:
# input: story_data_path
# logic:
    # find cover for story on goodreads by title 
    # save/download cover pictures in story_covers/
    # save path + other story cover data (e.g isbn, etc...) back to story data
def get_story_cover(story_data_path):

    with open(story_data_path, "r", encoding="utf-8") as f:
        story_data = json.load(f)
    
    story_title = story_data["title"]
    cover_info = fetch_goodreads_cover_by_title(story_title, size="l")
    
    #determine story cover path and save 
    story_cover_path = story_data['title'].lower().replace(' ', '-') + "-" + "coverg"
    story_cover_path = story_cover_path.replace("’", "'")   # Normalize the path to replace curly apostrophes with straight ones
    story_cover_path = story_cover_path.replace(",", "")    # Normalize the path to replace commas
    story_cover_path = os.path.join(PATHS["story_covers"], story_cover_path + ".jpg")     # Use the configured path
    
    try:
        open(story_cover_path,"wb").write(cover_info["cover_bytes"])
        print("✅ Story Cover Saved")
    except:
        print("❌ ERROR: Story Cover Failed Saving")
        return 


    cover_data = {
        "cover_path_file": story_cover_path,
        "cover_url_used": cover_info.get("cover_url_used",""),
        "goodreads_book_id": cover_info.get("goodreads_book_id",""),
        "page_url": cover_info.get("page_url",""),
        "canonical_url": cover_info.get("canonical_url",""),
        "page_url": cover_info.get("page_url",""),
        "isbn13": cover_info.get("isbn13",""),
        "isbn10": cover_info.get("isbn10",""),
        "asin": cover_info.get("asin","")
    }


     # 4) write back into story_data.json under "metadata"
    try:
        story_data["cover_data"] = cover_data
        with open(story_data_path, "w", encoding="utf-8") as f:
            json.dump(story_data, f, ensure_ascii=False, indent=2)
        print("✅ Story Data Updated with Cover")
    except:
        print("❌ ERROR: Story Data Failed Updating")
        return 
    
    time.sleep(3)
    return 


def manually_set_cover(story_data_path, cover_path):
    with open(story_data_path, "r", encoding="utf-8") as f:
        story_data = json.load(f)

    cover_data = {
            "cover_path_file": cover_path,
            "cover_url_used":"",
            "goodreads_book_id": "",
            "page_url": "",
            "canonical_url": "",
            "page_url": "",
            "isbn13": "",
            "isbn10": "",
            "asin": ""
        }

    story_data["cover_data"] = cover_data
    with open(story_data_path, "w", encoding="utf-8") as f:
        json.dump(story_data, f, ensure_ascii=False, indent=2)
    print("✅ Manually Set Story Cover")


# test_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/story_data/crime-and-punishment-rodion-raskolnikov.json"
# get_story_cover(test_path)



   


# info = fetch_goodreads_cover_by_title("The Old Man and the Sea", size="l")
# if info:
#     open("romeo_juliet.jpg","wb").write(info["cover_bytes"])
#     print({k: v for k, v in info.items() if k != "cover_bytes"})

