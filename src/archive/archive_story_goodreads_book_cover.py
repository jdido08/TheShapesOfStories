import re, urllib.parse, requests, json
from bs4 import BeautifulSoup
from typing import Optional, Tuple, Dict, Any



HDRS = {"User-Agent": "Mozilla/5.0", "Accept-Language": "en-US,en;q=0.9"}
SIZE_RE = re.compile(r"(/books/\d+)([sml])(/[^/?#]+\.(?:jpe?g|png|webp))", re.I)

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

    return data

# --- Example ---
info = fetch_goodreads_cover_by_title("Romeo and Juliet", size="l")
if info:
    open("romeo_juliet.jpg","wb").write(info["cover_bytes"])
    print({k: v for k, v in info.items() if k != "cover_bytes"})

