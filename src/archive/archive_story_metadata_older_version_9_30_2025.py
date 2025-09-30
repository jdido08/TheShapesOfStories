# core_metadata.py — v5
# Deterministic pipeline: Open Library → Wikidata → cleaned Google Books,
# then authority normalization (LoC subjects/genre; WD places→country/coords).
# Deps: requests
from __future__ import annotations
import requests, time, unicodedata, re
from typing import Dict, Any, List, Optional, Tuple

# -------------------- endpoints --------------------
OL_SEARCH = "https://openlibrary.org/search.json"
OL_WORK   = "https://openlibrary.org/works/{work_id}.json"
WD_API    = "https://www.wikidata.org/w/api.php"
GB_SEARCH = "https://www.googleapis.com/books/v1/volumes"
LOC_SUBJ_SUGGEST = "https://id.loc.gov/authorities/subjects/suggest/"
LOC_GENRE_SUGGEST = "https://id.loc.gov/authorities/genreForms/suggest/"

UA = {"User-Agent":"ShapesOfStories/1.4 (+core-metadata)"}

# -------------------- tiny cache --------------------
_CACHE: Dict[str, Any] = {}

def _cache_get(key): return _CACHE.get(key)
def _cache_put(key, val): _CACHE[key] = val; return val

# -------------------- utils --------------------
def _req_with_backoff(url, params=None, timeout=25, tries=3, base_sleep=0.8):
    cache_key = f"{url}|{str(params)}"
    c = _cache_get(cache_key)
    if c is not None: return c
    for i in range(tries):
        try:
            r = requests.get(url, params=params, headers=UA, timeout=timeout)
            if r.status_code == 200:
                return _cache_put(cache_key, r.json())
        except requests.RequestException:
            pass
        time.sleep(base_sleep * (2 ** i))
    return None

def _norm(s:str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
    s = re.sub(r"\s+", " ", s.lower().strip())
    return s

def _author_tokens(author:str) -> List[str]:
    a = _norm(author)
    toks = [t for t in re.split(r"[^a-z0-9]+", a) if t]
    if "dostoevsk" in a or "dostoyevsk" in a:
        toks += ["dostoevsky","dostoyevsky","dostoievski","dostoevski"]
    return list(dict.fromkeys(toks))

def _casefold_set(xs):
    seen, out = set(), []
    for x in xs or []:
        k = (x or "").strip()
        if not k: continue
        cf = k.casefold()
        if cf not in seen:
            seen.add(cf); out.append(k)
    return out

# ISO 639 mini-map for common codes emitted by OL
_LANG_MAP = {
    "eng":"English","rus":"Russian","spa":"Spanish","fre":"French","fra":"French","ger":"German","deu":"German",
    "ita":"Italian","por":"Portuguese","chi":"Chinese","zho":"Chinese","jpn":"Japanese","ara":"Arabic","hin":"Hindi"
}

# -------------------- Open Library --------------------
def get_ol_metadata(work_id:str) -> Dict[str, Any]:
    j = _req_with_backoff(OL_WORK.format(work_id=work_id), timeout=25, tries=3)
    if not j: return {}
    subjects = j.get("subjects", []) or []
    places   = j.get("subject_places", []) or []
    times    = j.get("subject_times", []) or []
    langs    = j.get("languages", []) or []
    lang_codes = []
    for lang in langs:
        key = lang.get("key","")
        if "/" in key: lang_codes.append(key.split("/")[-1])
    return {
        "openlibrary": {
            "work_id": work_id,
            "title": j.get("title"),
            "subjects": subjects,
            "subject_places": places,
            "subject_times": times,
            "languages": lang_codes
        }
    }

def resolve_ol_work_id(title:str, author:str, year:Optional[int]=None) -> Optional[str]:
    primary = _req_with_backoff(OL_SEARCH, {"title": title, "author": author, "limit": 30}, timeout=25, tries=3)
    docs = (primary or {}).get("docs", [])
    if not docs:
        fallback = _req_with_backoff(OL_SEARCH, {"q": f"{title} {author}", "limit": 30}, timeout=25, tries=3)
        docs = (fallback or {}).get("docs", [])
    if not docs: 
        return None

    nt, atoks = _norm(title), _author_tokens(author)

    def candidate_work_key(doc):
        if "work_key" in doc and doc["work_key"]:
            return doc["work_key"][0]
        for s in doc.get("seed",[]) or []:
            if isinstance(s, str) and s.startswith("/works/"):
                return s
        if isinstance(doc.get("key"), str) and doc["key"].startswith("/works/"):
            return doc["key"]
        return None

    scored = []
    seen = set()
    for d in docs:
        wk = candidate_work_key(d)
        if not wk: 
            continue
        wid = wk.split("/")[-1]
        if wid in seen: 
            continue
        seen.add(wid)

        base = 0
        t = _norm(d.get("title",""))
        if t == nt: base += 3
        elif nt in t or t in nt: base += 2
        auths = [_norm(a) for a in d.get("author_name",[]) if a]
        if any(any(tok in a for tok in atoks) for a in auths): base += 2
        if year:
            if d.get("first_publish_year")==year: base += 2
            elif year in (d.get("publish_year") or []): base += 1

        ol = get_ol_metadata(wid) or {}
        meta = ol.get("openlibrary", {})
        richness = len(meta.get("subjects",[])) + len(meta.get("subject_places",[])) + len(meta.get("subject_times",[]))
        lang_bonus = 1 if meta.get("languages") else 0
        scored.append((base + 0.5*richness + lang_bonus, wid))

    if not scored:
        return None
    scored.sort(reverse=True)
    return scored[0][1]

# -------------------- Wikidata (helpers) --------------------
def wd_get_entities(qids:List[str], props="labels|claims", lang="en") -> Dict[str,Any]:
    if not qids: return {}
    j = _req_with_backoff(
        WD_API,
        {"action":"wbgetentities","format":"json","languages":lang,"props":props,"ids":"|".join(qids)},
        timeout=25, tries=3
    )
    return j.get("entities",{}) if j else {}

def _claim_qids(ent:Dict[str,Any], pid:str) -> List[str]:
    out = []
    for sn in ent.get("claims",{}).get(pid,[]) or []:
        dv = sn.get("mainsnak",{}).get("datavalue",{})
        if dv.get("type")=="wikibase-entityid":
            out.append(f"Q{dv['value']['numeric-id']}")
    return out

def wd_search_author_qid(author:str) -> Optional[str]:
    j = _req_with_backoff(
        WD_API,
        {"action":"wbsearchentities","format":"json","language":"en","type":"item","search": author, "limit": 5},
        timeout=15, tries=3
    )
    if not j or not j.get("search"): return None
    return j["search"][0]["id"]

def wd_rest_lookup(title:str, author:str, year:Optional[int]) -> Dict[str,Any]:
    search = _req_with_backoff(
        WD_API,
        {"action":"wbsearchentities","format":"json","language":"en","type":"item","search": title, "limit": 25},
        timeout=15, tries=2
    )
    if not search or not search.get("search"):
        return {}
    cand_qids = [s["id"] for s in search["search"]][:25]
    ents = wd_get_entities(cand_qids, props="labels|claims")

    WRITTEN_WORK = {"Q47461344","Q7725634","Q8261","Q49848","Q25379"}
    work_qids, genres, subjects, places, countries, langs = set(), set(), set(), set(), set(), set()
    to_label = set()
    author_norm = _norm(author)

    def author_labels(qids:List[str]) -> List[str]:
        d = wd_get_entities(qids, props="labels")
        return [_norm(v.get("labels",{}).get("en",{}).get("value","")) for v in d.values()]

    for qid, ent in ents.items():
        inst = set(_claim_qids(ent, "P31"))
        if not (inst & WRITTEN_WORK):
            continue
        authors = set(_claim_qids(ent, "P50"))
        if not authors:
            continue
        auth_names = author_labels(list(authors))
        if not any(a and (author_norm in a or a in author_norm) for a in auth_names):
            continue
        if year and "P577" in ent.get("claims",{}):
            ok = False
            for sn in ent["claims"]["P577"]:
                t = sn.get("mainsnak",{}).get("datavalue",{}).get("value",{}).get("time","")
                if str(year) in t:
                    ok = True; break
            if not ok:
                continue

        work_qids.add(qid)
        for pid, collector in [("P136", genres), ("P921", subjects), ("P840", places), ("P495", countries), ("P407", langs)]:
            qs = _claim_qids(ent, pid); collector.update(qs); to_label.update(qs)

    if not work_qids:
        return {}

    lab_ents = wd_get_entities(list(to_label)[:50], props="labels")
    def _labset(qids): 
        return sorted({lab_ents.get(q,{}).get("labels",{}).get("en",{}).get("value", q) for q in qids})

    return {
        "wikidata": {
            "work_qids": sorted(work_qids),
            "genres": _labset(genres),
            "main_subjects": _labset(subjects),
            "narrative_locations": _labset(places),
            "countries_of_origin": _labset(countries),
            "languages": _labset(langs),
        }
    }

def get_wd_metadata(title:str, author:str, year:Optional[int]) -> Dict[str,Any]:
    auth_qid = wd_search_author_qid(author)
    if not auth_qid:
        return wd_rest_lookup(title, author, year)

    search = _req_with_backoff(
        WD_API,
        {"action":"wbsearchentities","format":"json","language":"en","type":"item","search": title, "limit": 25},
        timeout=15, tries=3
    )
    if not search or not search.get("search"):
        return {}

    cand_qids = [s["id"] for s in search["search"]]
    ents = wd_get_entities(cand_qids, props="labels|claims")
    WRITTEN_WORK = {"Q47461344","Q7725634","Q8261","Q49848","Q25379"}

    def title_sim(a:str, b:str) -> float:
        a, b = _norm(a), _norm(b)
        at, bt = set(a.split()), set(b.split())
        return len(at & bt) / max(1, len(at|bt))

    want = set()
    for qid, ent in ents.items():
        inst = set(_claim_qids(ent, "P31"))
        if not (inst & WRITTEN_WORK): 
            continue
        if auth_qid not in set(_claim_qids(ent, "P50")):
            continue
        lbl = ent.get("labels",{}).get("en",{}).get("value","")
        if title_sim(lbl, title) < 0.4:
            continue
        if year and "P577" in ent.get("claims",{}):
            ok = False
            for sn in ent["claims"]["P577"]:
                t = sn.get("mainsnak",{}).get("datavalue",{}).get("value",{}).get("time","")
                if str(year) in t: ok = True; break
            if not ok:
                continue
        want.add(qid)

    if not want:
        return wd_rest_lookup(title, author, year)

    ents2 = wd_get_entities(list(want), props="labels|claims")
    genres, subjects, places, countries, langs, to_label = set(), set(), set(), set(), set(), set()
    for qid, ent in ents2.items():
        for pid, collector in [("P136", genres), ("P921", subjects), ("P840", places), ("P495", countries), ("P407", langs)]:
            qs = _claim_qids(ent, pid); collector.update(qs); to_label.update(qs)

    lab_ents = wd_get_entities(list(to_label)[:50], props="labels")
    def lab(q): return lab_ents.get(q,{}).get("labels",{}).get("en",{}).get("value", q)
    return {
        "wikidata": {
            "work_qids": sorted(want),
            "genres": sorted({lab(x) for x in genres}),
            "main_subjects": sorted({lab(x) for x in subjects}),
            "narrative_locations": sorted({lab(x) for x in places}),
            "countries_of_origin": sorted({lab(x) for x in countries}),
            "languages": sorted({lab(x) for x in langs}),
        }
    }

def wd_to_openlibrary_work_qid_preferred(work_qids:List[str]) -> Optional[str]:
    if not work_qids: return None
    ents = wd_get_entities(work_qids, props="claims")
    for qid, ent in ents.items():
        for sn in ent.get("claims",{}).get("P648",[]) or []:  # Open Library ID (work)
            dv = sn.get("mainsnak",{}).get("datavalue",{})
            if dv and dv.get("type")=="string":
                olid = dv["value"].strip()
                if re.match(r"^OL\d+W$", olid):
                    return olid
    return None

# -------------------- Google Books (cleaned categories) --------------------
def get_gb_categories(title:str, author:str) -> List[str]:
    q = f'intitle:"{title}" inauthor:"{author}"'
    j = _req_with_backoff(GB_SEARCH, {"q": q, "maxResults": 10, "printType":"books"}, timeout=20, tries=2)
    raw = []
    if j and j.get("items"):
        for it in j["items"]:
            raw.extend(it.get("volumeInfo", {}).get("categories", []) or [])
    cats = set()
    for c in raw:
        for part in re.split(r"\s*/\s*", c):
            cats.add(part.strip())
    drop_re = re.compile(r"(?i)\b(english|american|russian|french|german|italian|spanish)\s+fiction\b")
    cleaned = [c for c in cats if not drop_re.search(c)]
    MAPPING = {
        "Classics": "Classics",
        "Literary": "Literary Fiction",
        "Mystery & Detective": "Mystery",
        "Mystery": "Mystery",
        "Crime": "Crime",
        "Psychological": "Psychological Fiction",
        "Thrillers": "Thriller",
        "Courtroom": "Courtroom Drama",
        "Philosophy": "Philosophical Fiction",
        "Fiction": "Fiction",
    }
    normalized = []
    for c in cleaned:
        key = next((k for k in MAPPING if c.lower()==k.lower() or c.lower().startswith(k.lower())), None)
        if key: normalized.append(MAPPING[key])
    return sorted(set(normalized))

# -------------------- Country association & era --------------------
_COUNTRY_NORMALIZE = {
    "russian empire": "Russia", "russian federation": "Russia",
    "usa": "United States", "united states of america": "United States",
    "uk": "United Kingdom", "england":"United Kingdom"
}
def _normalize_country(label: str) -> str:
    k = (label or "").strip()
    if not k: return k
    mapped = _COUNTRY_NORMALIZE.get(k.casefold())
    return mapped or k

def choose_country_association(wd_countries:List[str], ol_places:List[str], author_nationalities:Optional[List[str]]=None) -> Optional[str]:
    if wd_countries:
        return _normalize_country(wd_countries[0])
    country_regex = re.compile(r"\b(Russia|Russian Federation|United States|USA|England|United Kingdom|UK|France|Italy|Germany|Spain|China|Japan|India|Brazil|Canada|Mexico)\b", re.I)
    for p in ol_places:
        m = country_regex.search(p or "")
        if m:
            val = m.group(1)
            if val.upper() in {"USA"}: return "United States"
            if val.lower().startswith("united kingdom") or val.upper() in {"UK","England"}: return "United Kingdom"
            if val.lower().startswith("russian"): return "Russia"
            return val
    for p in ol_places:
        parts = [x.strip() for x in p.split(",")]
        if len(parts)>=2:
            return parts[-1]
    if author_nationalities:
        return author_nationalities[0]
    return None

def _derive_era(year: int | None):
    if not year: 
        return []
    decade = f"{(year//10)*10}s"
    century = f"{(year-1)//100 + 1}th century"
    return [decade, century]

# -------------------- LoC normalization (subjects & genre) --------------------
# Add at top (with your other endpoints)
LOC_SEARCH = "https://id.loc.gov/search/"

# Replace your _loc_suggest() with this more robust version.
# It tries suggest first; if that fails or returns non-URIs, it falls back to id.loc.gov/search?format=json.
def _loc_suggest(url: str, term: str, kind: str = "subjects") -> Optional[Dict[str, str]]:
    term = (term or "").strip()
    if not term:
        return None

    # 1) Try suggest (fast, lightweight)
    j = _req_with_backoff(url, {"q": term}, timeout=12, tries=2)
    try:
        # suggest returns: [query, [labels], [ids], ...]
        labels = j[1] if isinstance(j, list) and len(j) > 2 else []
        ids    = j[2] if isinstance(j, list) and len(j) > 2 else []
        for lab, uri in zip(labels, ids):
            if isinstance(uri, str) and uri.startswith("http"):
                return {"label": lab, "uri": uri}
    except Exception:
        pass  # fall through to search

    # 2) Fallback: full-text search (JSON)
    # Filter to the correct authority branch (subjects vs genreForms).
    search_kind = "subjects" if kind == "subjects" else "genreForms"
    qparams = {"q": term, "format": "json"}
    s = _req_with_backoff(f"{LOC_SEARCH}{search_kind}", qparams, timeout=12, tries=2)
    try:
        # search JSON structure: {"results": [{"uri": "...", "title": "..."} ...]}
        for rec in (s.get("results") or []):
            uri = rec.get("uri", "")
            if isinstance(uri, str) and uri.startswith("http"):
                lab = rec.get("title") or rec.get("label") or term
                return {"label": lab, "uri": uri}
    except Exception:
        return None

    return None

def loc_normalize_subjects(subjects: List[str]) -> List[Dict[str,str]]:
    out = []
    for s in subjects or []:
        hit = _loc_suggest(LOC_SUBJ_SUGGEST, s, kind="subjects")
        if hit:
            out.append({"label": hit["label"], "uri": hit["uri"], "scheme": "LCSH"})
    # dedupe by URI
    seen, dedup = set(), []
    for d in out:
        if d["uri"] not in seen:
            seen.add(d["uri"]); dedup.append(d)
    return dedup

def loc_normalize_genres(genres: List[str]) -> List[Dict[str,str]]:
    candidates = []
    for g in genres or []:
        # Prefer literary genreForms; try the exact term first
        hit = _loc_suggest(LOC_GENRE_SUGGEST, g, kind="genreForms")
        if hit:
            candidates.append(hit)
        # If the first hit looks like film/TV or doesn’t contain "fiction", try "<term> fiction"
        if not candidates or any(x in candidates[-1]["label"].lower() for x in ["film", "television", "radio"]) \
           or "fiction" not in candidates[-1]["label"].lower():
            alt = _loc_suggest(LOC_GENRE_SUGGEST, f"{g} fiction", kind="genreForms")
            if alt:
                candidates.append(alt)

    # Score & pick best per input
    def score(d, orig):
        L = d["label"].lower(); o = (orig or "").lower()
        return (2 if "fiction" in L else 0) \
             + (-2 if any(t in L for t in ["film","television","radio"]) else 0) \
             + (1 if (L == o or L.startswith(o)) else 0)

    picked = []
    for g in genres or []:
        best, best_s = None, -999
        for d in candidates:
            s = score(d, g)
            if s > best_s:
                best, best_s = d, s
        if best:
            picked.append({**best, "scheme":"LCGFT"})

    # Dedup by URI
    seen, out = set(), []
    for d in picked:
        if d["uri"] not in seen:
            seen.add(d["uri"]); out.append(d)
    return out

# -------------------- Wikidata place → country/coords --------------------
def wd_place_normalize(place_label: str) -> Optional[Dict[str,Any]]:
    if not place_label: return None
    # 1) search the place
    s = _req_with_backoff(
        WD_API, {"action":"wbsearchentities","format":"json","language":"en","type":"item","search": place_label, "limit": 5},
        timeout=15, tries=2
    )
    if not s or not s.get("search"): return None
    cand_qids = [it["id"] for it in s["search"]][:5]
    ents = wd_get_entities(cand_qids, props="labels|claims")
    best = None
    for qid, ent in ents.items():
        # Prefer items that have a country (P17)
        countries = _claim_qids(ent, "P17")
        if countries:
            best = (qid, ent); break
        best = best or (qid, ent)
    if not best: return None
    qid, ent = best
    # Resolve country label(s)
    c_qids = _claim_qids(ent, "P17")
    c_ents = wd_get_entities(c_qids, props="labels") if c_qids else {}
    country = None
    if c_ents:
        for v in c_ents.values():
            country = v.get("labels",{}).get("en",{}).get("value")
            if country: break
    # Coordinates P625
    lat = lon = None
    for sn in ent.get("claims",{}).get("P625",[]) or []:
        dv = sn.get("mainsnak",{}).get("datavalue",{}).get("value",{})
        lat = dv.get("latitude"); lon = dv.get("longitude")
        break
    label = ent.get("labels",{}).get("en",{}).get("value", place_label)
    return {"label": label, "wikidata_qid": qid, "country": country, "lat": lat, "lon": lon}

# -------------------- Post-processing & normalization --------------------
_CANON_GENRE_MAP = {
    "crime fiction": "Crime",
    "psychological fiction": "Psychological Fiction",
    "philosophical fiction": "Philosophical Fiction",
    "mystery": "Mystery",
    "classics": "Classics",
    "serialized fiction": None,   # drop (form, not display genre)
    "drama": "Drama",
}

_THEME_DROP_EXACT = {
    "adaptations","criticism and interpretation","readers for new literates",
    "slavic philology","fiction","fiction, psychological","psychological fiction"
}
_THEME_DROP_CONTAINS = ["textbooks","study guides","juvenile","guidebooks","translations"]

def _normalize_genres_display(genres):
    out = []
    for g in genres or []:
        gl = (g or "").strip(); 
        if not gl: continue
        key = gl.casefold()
        mapped = _CANON_GENRE_MAP.get(key)
        if mapped is None:
            continue
        out.append(mapped or gl)
    # title-case consistent display
    return sorted(set(out), key=str.lower)

def _clean_themes_display(themes):
    cleaned = []
    for t in themes or []:
        tl = (t or "").strip()
        if not tl: continue
        c = tl.casefold()
        if c in _THEME_DROP_EXACT: 
            continue
        if any(sub in c for sub in _THEME_DROP_CONTAINS):
            continue
        cleaned.append(tl)
    return _casefold_set(cleaned)

def _augment_places_with_country(places, country):
    if not country: 
        return _casefold_set(places or [])
    out = []
    for p in places or []:
        pl = (p or "").strip()
        if not pl: continue
        if country.lower() in pl.lower():
            out.append(pl)
        else:
            out.append(f"{pl}, {country}")
    return _casefold_set(out)

def normalize_core_metadata(result: dict) -> dict:
    story = result.get("story", {})
    # Country normalize
    ca = story.get("country_association")
    story["country_association"] = _normalize_country(ca) if ca else None

    # Language normalize
    lang = story.get("language")
    if lang and len(lang) == 3:
        story["language"] = _LANG_MAP.get(lang.lower(), lang)
    elif lang:
        story["language"] = lang.title()

    # Display genres/themes cleanup
    story["genre"] = _normalize_genres_display(story.get("genre"))
    story["themes"] = _clean_themes_display(story.get("themes"))

    # Places → add country textually for display
    story["setting_places"] = _augment_places_with_country(
        story.get("setting_places"), story.get("country_association")
    )

    # Era fallback
    if not story.get("setting_times"):
        y = (result.get("input") or {}).get("year")
        story["setting_times"] = _derive_era(y)

    # -------- Authority normalization outputs (kept separately) --------
    normalized = result.setdefault("normalized", {})
    # LCSH for themes
    normalized["themes_lcsh"] = loc_normalize_subjects(story.get("themes"))
    # LCGFT for genres
    normalized["genres_lcgft"] = loc_normalize_genres(story.get("genre"))
    # WD place reconciliation
    norm_places = []
    for p in story.get("setting_places") or []:
        hit = wd_place_normalize(p)
        if hit:
            hit["country"] = _normalize_country(hit.get("country"))
            norm_places.append(hit)
    # de-dup by QID/label
    seen = set(); places_dedup = []
    for d in norm_places:
        k = d.get("wikidata_qid") or d.get("label")
        if k in seen: continue
        seen.add(k); places_dedup.append(d)
    normalized["places_wikidata"] = places_dedup

    result["story"] = story
    return result

# -------------------- Orchestrator --------------------
def build_core_metadata(title:str, author:str, year:Optional[int]=None) -> Dict[str,Any]:
    result = {
        "input": {"title": title, "author": author, "year": year},
        "ids": {},
        "story": {
            "language": None,
            "genre": [],
            "themes": [],
            "setting_places": [],
            "setting_times": [],
            "country_association": None
        },
        "source_provenance":[]
    }

    # 1) Open Library: resolve & pull
    work_id = resolve_ol_work_id(title, author, year)
    if work_id:
        ol = get_ol_metadata(work_id)
        result["ids"]["openlibrary_work"] = work_id
        if ol:
            subjects = ol["openlibrary"]["subjects"]
            result["story"]["themes"] = sorted(set(subjects))
            result["story"]["setting_places"] = sorted(set(ol["openlibrary"]["subject_places"]))
            result["story"]["setting_times"]  = sorted(set(ol["openlibrary"]["subject_times"]))
            if ol["openlibrary"]["languages"]:
                # OL returns 3-letter codes like 'rus'
                code = ol["openlibrary"]["languages"][0]
                result["story"]["language"] = _LANG_MAP.get(code.lower(), code)
            result["source_provenance"].append({"source":"openlibrary","work_id":work_id})
    else:
        result["source_provenance"].append({"source":"openlibrary","error":"no_work_match"})

    # 2) Wikidata: author-first work resolution + properties
    wd = get_wd_metadata(title, author, year)
    if wd:
        result["ids"]["wikidata_work_qids"] = wd["wikidata"]["work_qids"]
        if wd["wikidata"]["genres"]:
            result["story"]["genre"] = sorted(set(result["story"]["genre"]) | set(wd["wikidata"]["genres"]))
        if wd["wikidata"]["main_subjects"]:
            result["story"]["themes"] = sorted(set(result["story"]["themes"]) | set(wd["wikidata"]["main_subjects"]))
        if wd["wikidata"]["narrative_locations"]:
            result["story"]["setting_places"] = sorted(set(result["story"]["setting_places"]) | set(wd["wikidata"]["narrative_locations"]))
        if not result["story"]["language"] and wd["wikidata"]["languages"]:
            result["story"]["language"] = wd["wikidata"]["languages"][0]
        result["source_provenance"].append({"source":"wikidata","qids":wd["wikidata"]["work_qids"]})
    else:
        result["source_provenance"].append({"source":"wikidata","error":"no_rows"})

    # 3) Crosswalk WD → Open Library via P648 (canonical OL record; richer subjects)
    preferred_olid = wd_to_openlibrary_work_qid_preferred(result.get("ids",{}).get("wikidata_work_qids",[]))
    if preferred_olid and preferred_olid != result["ids"].get("openlibrary_work"):
        ol2 = get_ol_metadata(preferred_olid)
        if ol2:
            result["ids"]["openlibrary_work"] = preferred_olid
            result["story"]["themes"] = sorted(set(result["story"]["themes"]) | set(ol2["openlibrary"]["subjects"]))
            result["story"]["setting_places"] = sorted(set(result["story"]["setting_places"]) | set(ol2["openlibrary"]["subject_places"]))
            result["story"]["setting_times"]  = sorted(set(result["story"]["setting_times"])  | set(ol2["openlibrary"]["subject_times"]))
            if not result["story"]["language"] and ol2["openlibrary"]["languages"]:
                code = ol2["openlibrary"]["languages"][0]
                result["story"]["language"] = _LANG_MAP.get(code.lower(), code)
            result["source_provenance"].append({"source":"openlibrary","work_id":preferred_olid,"reason":"wd_p648"})

    # 4) Google Books fallback for genre (cleaned)
    if not result["story"]["genre"]:
        cats = get_gb_categories(title, author)
        result["story"]["genre"] = cats or []
        if cats: result["source_provenance"].append({"source":"google_books","reason":"genre_fallback"})

    # 5) Country association
    wd_countries = wd.get("wikidata",{}).get("countries_of_origin",[]) if wd else []
    ol_places = result["story"]["setting_places"]
    result["story"]["country_association"] = choose_country_association(wd_countries, ol_places, author_nationalities=None)

    # 6) Normalize everything to authorities + tidy display
    result = normalize_core_metadata(result)
    return result


# __________________ LLM CLEAN UP ___________________

# llm_referee.py
import json, textwrap

ALLOWED_GENRES = [
    "Classics","Literary Fiction","Historical Fiction","Crime","Mystery",
    "Psychological Fiction","Philosophical Fiction","Southern Gothic",
    "Domestic Fiction","Legal Fiction","Coming-of-Age","Satire","Magical Realism"
]

ALLOWED_COUNTRIES = [
    "United States","United Kingdom","Russia","France","Germany","Italy","Spain","Japan","China","India",
    "Brazil","Canada","Mexico","Ireland","Australia","Argentina","Chile","Colombia","Nigeria","Kenya",
    "South Africa","Algeria","Egypt","Albania","Czech Republic","Poland","Norway","Sweden","Denmark",
    "Finland","Netherlands","Belgium","Greece","Turkey","Portugal","Austria","Switzerland","Hungary",
    "Romania","Bulgaria","Serbia","Croatia"
]

def _system_msg(allowed_genres, allowed_countries):
    return textwrap.dedent(f"""
    You are a strict metadata normalizer. Use ONLY the evidence provided by the user.
    Return valid JSON exactly like:
    {{"genre":[], "setting_places":[], "country_association":null, "themes":[]}}

    Rules:
    - genre: up to 3 labels from this allowed set: {allowed_genres}
    - setting_places: 1–3 items; prefer "City, Country". If only region/state is clear, use that (e.g., "Alabama, United States").
    - country_association: one of {allowed_countries} or null.
    - themes: 3–5 concise concepts (nouns/short noun phrases). No genres, no settings, no spoilers. De-duplicate.
    - If uncertain, leave fields empty ([], null).
    """)

def _user_msg(evidence: dict):
    # Only evidence you already fetched — closed world
    return textwrap.dedent(f"""
    TITLE: {evidence.get('title')}
    AUTHOR: {evidence.get('author')}
    YEAR: {evidence.get('year')}

    EVIDENCE:
    - WD.P136 (genres): {evidence.get('wd_genres')}
    - WD.P840 (settings): {evidence.get('wd_settings')}
    - WD.P495 (countries): {evidence.get('wd_countries')}
    - WD.P921 (subjects): {evidence.get('wd_subjects')}
    - OL.subjects: {evidence.get('ol_subjects')}
    - GB.categories: {evidence.get('gb_categories')}
    - Description (optional): {evidence.get('description')}
    """)

def _clamp_output(data, allowed_genres, allowed_countries):
    # genre: allowed subset, max 3
    genres = [g for g in (data.get("genre") or []) if isinstance(g, str) and g in allowed_genres][:3]
    # settings: strings, non-empty, max 3
    settings = [s.strip() for s in (data.get("setting_places") or []) if isinstance(s, str) and s.strip()][:3]
    # country: allowed or None
    country = data.get("country_association")
    country = country if country in allowed_countries else None
    # themes: strings, non-empty, not genres, not place-y, max 5
    seen = set(); themes = []
    for t in (data.get("themes") or []):
        if not isinstance(t, str): continue
        lab = t.strip()
        if not lab: continue
        if lab in allowed_genres: continue
        if "," in lab: continue  # looks like "City, Country"
        key = lab.casefold()
        if key in seen: continue
        seen.add(key); themes.append(lab)
    return {
        "genre": genres,
        "setting_places": settings,
        "country_association": country,
        "themes": themes[:5],
    }

def refine_with_llm_labels_only_via_story_style(
    evidence: dict,
    llm_call,               # your function from story_style.py (see adapters below)
    allowed_genres = ALLOWED_GENRES,
    allowed_countries = ALLOWED_COUNTRIES,
    temperature: float = 0.1,
    max_tokens: int = 350,
):
    """
    llm_call can be either:
      A) messages-style: llm_call(messages=[{"role":"system","content":...},{"role":"user","content":...}], temperature=..., max_tokens=..., json=True) -> str(JSON)
      B) prompt-style:   llm_call(prompt: str, temperature=..., max_tokens=..., json=True) -> str(JSON)

    It must return a JSON string with keys: genre, setting_places, country_association, themes.
    """
    system = _system_msg(allowed_genres, allowed_countries)
    user   = _user_msg(evidence)

    # Try messages API first
    try:
        raw = llm_call(
            messages=[{"role":"system","content":system},{"role":"user","content":user}],
            temperature=temperature,
            max_tokens=max_tokens,
            json=True
        )
    except TypeError:
        # Fallback: single prompt API
        prompt = system + "\n\n" + user
        raw = llm_call(
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json=True
        )
    except Exception:
        return {"genre": [], "setting_places": [], "country_association": None, "themes": []}

    # Parse → clamp
    try:
        data = json.loads(raw)
    except Exception:
        return {"genre": [], "setting_places": [], "country_association": None, "themes": []}
    return _clamp_output(data, allowed_genres, allowed_countries)


# -------------------- quick test --------------------

def get_story_metadata(title, author, year):
    result = build_core_metadata(title, author, year)
    evidence = {
        "title": result["input"]["title"],
        "author": result["input"]["author"],
        "year": result["input"]["year"],
        "wd_genres": wd.get("wikidata", {}).get("genres", []) if isinstance(wd, dict) else [],
        "wd_settings": wd.get("wikidata", {}).get("narrative_locations", []) if isinstance(wd, dict) else [],
        "wd_countries": wd.get("wikidata", {}).get("countries_of_origin", []) if isinstance(wd, dict) else [],
        "wd_subjects": wd.get("wikidata", {}).get("main_subjects", []) if isinstance(wd, dict) else [],
        "ol_subjects": result["story"].get("themes", []),        # you already copy OL subjects here
        "gb_categories": result["story"].get("genre", []),       # your cleaned GB categories (optional)
        "description": None,                                     # optionally add a short description snippet
    }

    # Only call the LLM when you need it (genre empty or you want themes):
    need_llm = (not result["story"]["genre"]) or True  # set True if you always want themes

    refined = refine_with_llm_labels_only_via_story_style(
        evidence,
        llm_call=llm_call_messages,     # or llm_call_prompt
        temperature=0.1,
        max_tokens=350
    )

    # Merge back (honor your precedence rules)
    if refined["genre"]:
        result["story"]["genre"] = refined["genre"]
    if refined["setting_places"]:
        result["story"]["setting_places"] = refined["setting_places"]
    if refined["country_association"]:
        result["story"]["country_association"] = refined["country_association"]
    if refined["themes"]:
        result["story"]["themes"] = refined["themes"]

    result["source_provenance"].append({"source":"llm_referee","reason":"normalize_labels"})



print(get_story_metadata("To Kill a Mockingbird", "Harper Lee", 1960))
print(get_story_metadata("The Trial", "Franz Kafka", 1925))
print(get_story_metadata("The Stranger", "Albert Camus", 1942))
