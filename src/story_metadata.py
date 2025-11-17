# get_story_metadata() function:

# inputs:
# story_data.json
# extract title, author, year of story 

# Basic Logic
# 1.) Get metadata on story using Wikipedia, OpenLibrary, Wikidata, Google Books, etc..
#   - genre(s) --> do I also want to have like 'Classic' Tag ??
#   - setting(s) --> city, state, region, etc.. 
#   - theme(s)
#   - associated country
#   - series/universe ???
#.  - awards ??
# 2.) Use LLM to clean up and normalize metadata 
# 3.) Write clean/normalized metadata back to json 
# NOTE: the metadata here is NOT exhaustive. I think a lot fo collections will be manually assembled but this process can still be useful 


# why:
# meatadata will help:
# - the ability to search for stories
# - the ability to more easily create collections e.g. 
#   - The Shapes of Pittsburgh
#   - The Shapes of Love 
#   - The Shapes 

#!/usr/bin/env python3
"""
Compile canonical story metadata from OpenLibrary, Google Books, and Wikidata (REST-only),
optionally normalize with an LLM, and write back to story_data.json.

Usage:
  python story_metadata.py /path/to/story_data.json --llm off
  python story_metadata.py /path/to/story_data.json --llm on --llm-provider openai --llm-model gpt-4o-mini
  python story_metadata.py /path/to/story_data.json --wikidata off   # skip WD entirely

The script expects story_data.json to contain at least:
{
  "title": "To Kill a Mockingbird",
  "author": "Harper Lee",
  "year": 1960,
  ...
}
It will add/overwrite a "metadata" object with consolidated fields.
"""

from __future__ import annotations
import json, sys, time, re, argparse, logging, os, hashlib
from typing import Dict, Any, List, Optional
import requests
from urllib3.util.retry import Retry

# -----------------------
# HTTP session with retries (polite) + constants
# -----------------------
HTTP_TIMEOUT = 20  # seconds
CACHE_DIR = os.path.expanduser("~/.shapes_cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": "ShapesOfStories/1.0 (+https://theshapesofstories.com; contact: support@theshapesofstories.com)"
    })
    retry = Retry(
        total=6,
        connect=6,
        read=6,
        backoff_factor=0.6,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset(["GET", "HEAD"])
    )
    adapter = requests.adapters.HTTPAdapter(max_retries=retry)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s

def _cache_key(url: str, params: Dict[str, Any]) -> str:
    payload = url + "?" + "&".join(f"{k}={params[k]}" for k in sorted(params))
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()

def _cached_get_json(session: requests.Session, url: str, params: Dict[str, Any], timeout: int = HTTP_TIMEOUT) -> Dict[str, Any]:
    key = _cache_key(url, params)
    path = os.path.join(CACHE_DIR, key + ".json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    r = session.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    time.sleep(0.6)  # gentle throttle to be nice to public APIs
    return data

# -----------------------
# Tiny helpers
# -----------------------
def _clean(s: Optional[str]) -> Optional[str]:
    if not s: return None
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s or None

def _dedupe_keep_order(items: List[str]) -> List[str]:
    seen = set(); out = []
    for x in items or []:
        if not x: continue
        key = x.casefold()
        if key in seen: continue
        seen.add(key); out.append(x)
    return out

def _maybe_int_year(y) -> Optional[int]:
    try:
        yi = int(str(y)[:4])
        if 1000 <= yi <= 2100:
            return yi
    except Exception:
        pass
    return None

def _digits_isbn(s: str) -> str:
    return re.sub(r"[^0-9Xx]", "", s or "")

# -----------------------
# Source fetchers
# -----------------------
def fetch_openlibrary(title: str, author: Optional[str], year: Optional[int]) -> Dict[str, Any]:
    ses = _session()
    url = "https://openlibrary.org/search.json"
    params = {"title": title, "limit": 10}  # was 3
    if author: params["author"] = author
    if year:   params["publish_year"] = year
    r = ses.get(url, params=params, timeout=HTTP_TIMEOUT)
    r.raise_for_status()
    data = r.json()
    docs = data.get("docs", []) or []
    if not docs: return {}

    def _norm(s): return re.sub(r"[^a-z0-9]+", " ", (_clean(s) or "").lower()).strip()
    tnorm = _norm(title); anorm = _norm(author) if author else None

    def score(d):
        s = 0
        if _norm(d.get("title")) == tnorm: s += 3
        if anorm and any(_norm(a) == anorm for a in d.get("author_name", []) or []): s += 2
        if year and (year in (d.get("publish_year") or []) or d.get("first_publish_year") == year): s += 1
        # soft penalties for study guides/abridgements
        if re.search(r"(study guide|summary|cliffsnotes|sparknotes)", (_clean(d.get("title")) or "").lower()):
            s -= 2
        return s

    docs.sort(key=score, reverse=True)
    top = docs[:5]  # harvest top-5

    # Harvest fields across top hits
    subjects, places, times, series, isbns = [], [], [], [], []
    first_publish_year = None
    openlibrary_key = None
    for i, d in enumerate(top):
        subjects += d.get("subject", []) or []
        places   += d.get("place", []) or []
        times    += d.get("time", []) or []
        series   += d.get("series", []) or []
        isbns    += d.get("isbn", []) or []
        if i == 0:
            first_publish_year = d.get("first_publish_year") or first_publish_year
            openlibrary_key = d.get("key") or openlibrary_key

    return {
        "source": "openlibrary",
        "openlibrary_key": openlibrary_key,
        "title": top[0].get("title") if top else None,
        "authors": top[0].get("author_name", []) if top else [],
        "first_publish_year": first_publish_year,
        "subjects": _dedupe_keep_order(subjects),
        "subject_places": _dedupe_keep_order(places),
        "subject_times": _dedupe_keep_order(times),
        "series": _dedupe_keep_order(series),
        "isbns": _dedupe_keep_order(isbns)
    }


def fetch_openlibrary_work(openlibrary_key: Optional[str]) -> Dict[str, Any]:
    """Enrich using the Work endpoint if we have a /works/OL... key."""
    if not openlibrary_key or not str(openlibrary_key).startswith("/works/"):
        return {}
    ses = _session()
    url = f"https://openlibrary.org{openlibrary_key}.json"
    try:
        data = _cached_get_json(ses, url, params={}, timeout=HTTP_TIMEOUT)
    except Exception as e:
        logging.info("OpenLibrary Work fetch failed: %s", e)
        return {}
    subjects = data.get("subjects", []) or []
    places = data.get("subject_places", []) or []
    times = data.get("subject_times", []) or []
    return {
        "ol_work_subjects": subjects,
        "ol_work_places": places,
        "ol_work_times": times
    }

def fetch_googlebooks(title: str, author: Optional[str]) -> Dict[str, Any]:
    ses = _session()
    base = {"maxResults": 15, "printType": "books", "orderBy": "relevance"}
    def call(q):
        r = ses.get("https://www.googleapis.com/books/v1/volumes", params=dict(base, q=q), timeout=HTTP_TIMEOUT)
        r.raise_for_status(); return r.json().get("items", []) or []

    queries = [f'intitle:"{title}"' + (f' inauthor:"{author}"' if author else "")]
    # fallback looser query
    queries.append(f'"{title}"' + (f' {author}' if author else ""))

    items = []
    for q in queries:
        items = call(q)
        if items: break
    if not items: return {}

    def _norm(s): return re.sub(r"[^a-z0-9]+", " ", (_clean(s) or "").lower()).strip()
    tnorm = _norm(title); anorm = _norm(author) if author else None

    def score(it):
        v = it.get("volumeInfo", {}) or {}
        t = _norm(v.get("title"))
        s = 0
        if t == tnorm: s += 2
        if anorm and any(_norm(a) == anorm for a in v.get("authors", []) or []): s += 1
        # punish study guides/summaries
        if re.search(r"(study guide|summary|bright notes|cliffsnotes|sparknotes)", (_clean(v.get("title")) or "").lower()):
            s -= 3
        return s

    items.sort(key=score, reverse=True)
    top = items[:8]  # harvest top-8

    cats, descs, isbns, pub_years = [], [], [], []
    for it in top:
        v = it.get("volumeInfo", {}) or {}
        # categories
        cats += v.get("categories", []) or []
        # description (keep longest)
        d = v.get("description")
        if d: descs.append(d)
        # isbns
        for ident in v.get("industryIdentifiers", []) or []:
            if (ident.get("type", "") or "").upper().startswith("ISBN"):
                isbns.append(ident.get("identifier"))
        # year
        y = _maybe_int_year(v.get("publishedDate"))
        if y: pub_years.append(y)

    # choose best description by length
    desc = max(descs, key=len) if descs else None
    year = min(pub_years) if pub_years else None  # earliest publication among top-8

    return {
        "source": "googlebooks",
        "categories": _dedupe_keep_order(cats),
        "description": desc,
        "published_year": year,
        "isbns": _dedupe_keep_order(isbns)
    }


# -----------------------
# Wikipedia → Wikidata (REST-only; no SPARQL)
# -----------------------
# Acceptable P31s for "work", and the "edition" QID to exclude.
LITWORK_P31_WHITELIST = {"Q7725634", "Q8261", "Q47461344"}  # literary work, novel, written work
EDITION_QID = "Q3331189"

def _wiki_search_pageid(title: str, author: Optional[str]) -> Optional[int]:
    ses = _session()
    query = f'intitle:"{title}"'
    if author: query += f' {author}'
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": 5,
        "format": "json"
    }
    data = _cached_get_json(ses, url, params, timeout=HTTP_TIMEOUT)
    hits = data.get("query", {}).get("search", [])
    if not hits: return None
    # Prefer exact (case-insensitive) title match
    hits.sort(key=lambda h: 2 if h.get("title","").lower() == title.lower() else 0, reverse=True)
    return hits[0].get("pageid")

def _wiki_pageprops_qid(pageid: int) -> Optional[str]:
    ses = _session()
    url = "https://en.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "prop": "pageprops",
        "pageids": pageid,
        "format": "json"
    }
    data = _cached_get_json(ses, url, params, timeout=HTTP_TIMEOUT)
    pages = data.get("query", {}).get("pages", {})
    for p in pages.values():
        qid = p.get("pageprops", {}).get("wikibase_item")
        if qid and qid.startswith("Q"):
            return qid
    return None

def _resolve_qid_via_wikipedia(title: str, author: Optional[str]) -> Optional[str]:
    pid = _wiki_search_pageid(title, author)
    if not pid: return None
    return _wiki_pageprops_qid(pid)

def _wd_get_entity(session: requests.Session, qid: str) -> dict:
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    data = _cached_get_json(session, url, params={}, timeout=HTTP_TIMEOUT)
    return data["entities"][qid]

def _wd_claim_qids(ent: dict, prop: str) -> List[str]:
    ids = []
    for cl in ent.get("claims", {}).get(prop, []) or []:
        val = cl.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(val, dict) and val.get("id", "").startswith("Q"):
            ids.append(val["id"])
    return ids

def _wd_time_year(ent: dict, prop: str) -> Optional[int]:
    for cl in ent.get("claims", {}).get(prop, []) or []:
        t = cl.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("time")
        if not t: continue
        m = re.search(r"[+-](\d{4})", t or "")
        if m:
            y = int(m.group(1))
            if 1000 <= y <= 2100:
                return y
    return None

def _wd_labels_for(session: requests.Session, qids: List[str]) -> Dict[str, str]:
    if not qids: return {}
    out = {}
    url = "https://www.wikidata.org/w/api.php"
    for i in range(0, len(qids), 50):
        chunk = qids[i:i+50]
        params = {
            "action": "wbgetentities",
            "ids": "|".join(chunk),
            "props": "labels",
            "languages": "en",
            "format": "json"
        }
        data = _cached_get_json(session, url, params, timeout=HTTP_TIMEOUT)
        for q, ent in data.get("entities", {}).items():
            lab = (ent.get("labels", {}).get("en") or {}).get("value")
            if lab: out[q] = lab
    return out

def _wd_entity_label(ent: dict) -> str:
    return (ent.get("labels", {}).get("en") or {}).get("value", "")

def _wd_is_literary_work(ent: dict) -> bool:
    p31 = set(_wd_claim_qids(ent, "P31"))
    if EDITION_QID in p31: return False
    return bool(p31 & LITWORK_P31_WHITELIST)

def _wd_author_labels(session: requests.Session, ent: dict) -> List[str]:
    author_q = _wd_claim_qids(ent, "P50")
    labels = _wd_labels_for(session, author_q)
    return [lab.lower() for lab in labels.values()]

def fetch_wikidata_rest(title: str, author: Optional[str]) -> Dict[str, Any]:
    """
    REST-only Wikidata fetch:
      1) Resolve QID via Wikipedia (pageprops.wikibase_item), else fallback to wbsearchentities
      2) Load entity JSON, ensure it's a work (not edition), confirm author if provided
      3) Extract P136/P179/P840/P495/P921/P166/P577 and resolve labels
    """
    ses = _session()
    title_clean = _clean(title) or ""
    author_clean = (_clean(author) or "").lower() if author else None

    # 1) Try Wikipedia for exact QID
    qid = _resolve_qid_via_wikipedia(title_clean, author)
    candidates = [qid] if qid else []

    # 2) Fallback: wbsearchentities
    if not candidates:
        url = "https://www.wikidata.org/w/api.php"
        params = {
            "action": "wbsearchentities",
            "search": title_clean,
            "language": "en",
            "type": "item",
            "limit": 10,
            "format": "json",
        }
        data = _cached_get_json(ses, url, params, timeout=HTTP_TIMEOUT)
        candidates = [it["id"] for it in data.get("search", []) if it.get("id")]

    best_ent, best_score = None, -1
    for q in candidates:
        if not q: continue
        try:
            ent = _wd_get_entity(ses, q)
        except Exception:
            continue
        if not _wd_is_literary_work(ent):
            continue

        label = _wd_entity_label(ent).lower()
        score = 0
        if label == title_clean.lower(): score += 2
        if author_clean:
            auths = _wd_author_labels(ses, ent)
            if not auths or author_clean not in auths:
                # If QID came from Wikipedia, allow leniency; else enforce author
                if q != qid:
                    continue
            else:
                score += 2

        if score > best_score:
            best_ent, best_score = ent, score

    if not best_ent:
        logging.info("WD: no suitable work entity found via REST")
        return {}

    genre_q   = _wd_claim_qids(best_ent, "P136")
    series_q  = _wd_claim_qids(best_ent, "P179")
    loc_q     = _wd_claim_qids(best_ent, "P840")
    country_q = _wd_claim_qids(best_ent, "P495")
    theme_q   = _wd_claim_qids(best_ent, "P921")
    award_q   = _wd_claim_qids(best_ent, "P166")
    pub_year  = _wd_time_year(best_ent, "P577")

    all_qs = _dedupe_keep_order(genre_q + series_q + loc_q + country_q + theme_q + award_q)
    labels = _wd_labels_for(ses, all_qs)

    return {
        "source": "wikidata",
        "wikidata_qid": best_ent.get("id"),
        "genres": [labels.get(q) for q in genre_q if labels.get(q)],
        "series": [labels.get(q) for q in series_q if labels.get(q)],
        "narrative_locations": [labels.get(q) for q in loc_q if labels.get(q)],
        "associated_countries": [labels.get(q) for q in country_q if labels.get(q)],
        "themes": [labels.get(q) for q in theme_q if labels.get(q)],
        "awards": [labels.get(q) for q in award_q if labels.get(q)],
        "published_year": pub_year
    }

# -----------------------
# Consolidation / shaping
# -----------------------
def consolidate(openlib: Dict[str,Any], openlib_work: Dict[str,Any], gbooks: Dict[str,Any], wiki: Dict[str,Any]) -> Dict[str, Any]:
    # Genres
    genres = []
    genres += wiki.get("genres", [])
    genres += gbooks.get("categories", [])
    ol_genres = [s for s in openlib.get("subjects", []) if s and s[0].isalpha() and len(s) < 40]
    genres += ol_genres
    # Also seed from Work subjects
    for s in (openlib_work.get("ol_work_subjects") or []):
        if s and s[0].isalpha() and len(s) < 40:
            genres.append(s)

    # Themes
    themes = []
    themes += wiki.get("themes", [])
    theme_noise = set(x.lower() for x in ["fiction", "literature", "classic", "novel", "american literature"])
    for s in openlib.get("subjects", []) + (openlib_work.get("ol_work_subjects") or []):
        if s and s.lower() not in theme_noise:
            themes.append(s)

    # Settings: combine WD narrative locations + OL subject_places/times + Work places/times
    settings = []
    settings += wiki.get("narrative_locations", [])
    settings += openlib.get("subject_places", []) or []
    settings += openlib.get("subject_times", []) or []
    settings += openlib_work.get("ol_work_places", []) or []
    settings += openlib_work.get("ol_work_times", []) or []

    # Associated country
    countries = wiki.get("associated_countries", [])

    # Series / Universe
    series_or_universe = []
    series_or_universe += wiki.get("series", [])
    series_or_universe += openlib.get("series", [])

    # Awards
    awards = wiki.get("awards", [])

    # Year: prefer OL first_publish_year, else Wikidata, else Google Books
    year_candidates = [
        openlib.get("first_publish_year"),
        wiki.get("published_year"),
        gbooks.get("published_year")
    ]
    year = next((y for y in year_candidates if y), None)

    # ISBNs: combine, dedupe, prefer ISBN-13
    isbns = _dedupe_keep_order((openlib.get("isbns", []) or []) + (gbooks.get("isbns", []) or []))
    isbn13 = [i for i in isbns if len(_digits_isbn(i)) == 13]
    primary_isbns = isbn13 if isbn13 else isbns

    consolidated = {
        "genres": _dedupe_keep_order([_clean(x) for x in genres])[:30],
        "themes": _dedupe_keep_order([_clean(x) for x in themes])[:50],
        "settings": _dedupe_keep_order([_clean(x) for x in settings])[:50],
        "associated_countries": _dedupe_keep_order([_clean(x) for x in countries])[:10],
        "series_or_universe": _dedupe_keep_order([_clean(x) for x in series_or_universe])[:10],
        "awards": _dedupe_keep_order([_clean(x) for x in awards])[:30],
        "published_year": year,
        "primary_isbns": primary_isbns[:10],
        "description": gbooks.get("description")  # pass through for LLM theme derivation (not persisted after LLM)
    }

    # Trim obvious noise (very short/very long)
    for k in ["genres","themes","settings"]:
        consolidated[k] = [v for v in consolidated[k] if v and 2 <= len(v) <= 60]

    return consolidated

# -----------------------
# LLM normalization (optional)
# -----------------------
# from langchain.prompts import PromptTemplate
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from llm import load_config, get_llm, extract_json

# Controlled vocab (seed; expand as you grow)
# ---- Canon lists (compact but broad coverage) ----
CANON_GENRES = [
    "Literary Fiction","Historical Fiction","Science Fiction","Fantasy","Magical Realism",
    "Dystopian","Horror","Mystery","Crime & Detective","Thriller","Romance",
    "Young Adult","Middle Grade","Children's","Classics","Short Stories","Poetry","Drama",
    "Tragedy","Comedy","Satire","Gothic","Western","Adventure","Coming-of-Age",
    "Graphic Novel/Comics","Myth & Folklore","Fairy Tale & Retellings",
    "Narrative Nonfiction","Biography","Memoir","True Crime", "Humor"
]

CANON_THEMES = [
    "Love","Forbidden Love","Friendship","Family","Identity","Self-Discovery","Coming of Age",
    "Ambition","Power","Corruption","Justice","Prejudice","Inequality","Class & Society",
    "Freedom","Rebellion/Resistance","War","Violence","Survival","Courage","Sacrifice",
    "Revenge","Forgiveness","Redemption","Guilt","Grief","Loss & Mourning","Hope","Fear",
    "Morality","Good vs Evil","Fate vs Free Will","Destiny/Prophecy","Honor","Love vs Duty",
    "Tradition vs Change","Deception/Secrets","Miscommunication","Loyalty","Betrayal",
    "Memory","Truth","Isolation","Alienation","Poverty","Wealth & Greed",
    "Colonialism & Empire","Environment/Nature","Technology & Ethics","AI & Consciousness",
    "Religion & Faith"
]
GENRE_SYNONYMS = {
    "bildungsroman": "Coming-of-Age",
    "coming of age": "Coming-of-Age",
    "ya": "Young Adult",
    "new adult": "Young Adult",
    "sci fi": "Science Fiction",
    "science-fiction": "Science Fiction",
    "speculative fiction": "Science Fiction",   # you can keep this separate if you prefer
    "magical-realism": "Magical Realism",
    "urban fantasy": "Fantasy",
    "paranormal": "Fantasy",
    "detective": "Crime & Detective",
    "crime": "Crime & Detective",
    "police procedural": "Crime & Detective",
    "noir": "Crime & Detective",
    "psychological thriller": "Thriller",
    "gothic fiction": "Gothic",
    "fairy tale": "Fairy Tale & Retellings",
    "fairy tales": "Fairy Tale & Retellings",
    "folklore": "Myth & Folklore",
    "mythology": "Myth & Folklore",
    "graphic novel": "Graphic Novel/Comics",
    "comics": "Graphic Novel/Comics",
    "true-crime": "True Crime",
    "narrative nonfiction": "Narrative Nonfiction",
    "creative nonfiction": "Narrative Nonfiction",
    "classic": "Classics",
    "classics": "Classics",
    "humour": "Humor",
    "humorous": "Humor",
    "humorous fiction": "Humor",
    "comic": "Humor",
    "comic fiction": "Humor",
    "sci-fi": "Science Fiction",        # hyphenated variant
    "ya": "Young Adult", "YA": "Young Adult",
    "children": "Children's", "childrens": "Children's", "children’s": "Children's",
    "cozy mystery": "Mystery", "whodunit": "Mystery",
    "satirical": "Satire",              # descriptive → genre
    "romcom": "Comedy", "rom-com": "Comedy",
    "coming-of-age": "Coming-of-Age"   # hyphenated variant
}

THEME_SYNONYMS = {
    "self discovery": "Self-Discovery",
    "prejudice": "Prejudice",
    "racism": "Prejudice",
    "bigotry": "Prejudice",
    "discrimination": "Inequality",
    "social class": "Class & Society",
    "class": "Class & Society",
    "wealth": "Wealth & Greed",
    "greed": "Wealth & Greed",
    "poverty": "Poverty",
    "lies": "Deception/Secrets",
    "secrets": "Deception/Secrets",
    "deceit": "Deception/Secrets",
    "prophecy": "Destiny/Prophecy",
    "free will vs fate": "Fate vs Free Will",
    "good and evil": "Good vs Evil",
    "faith": "Religion & Faith",
    "environment": "Environment/Nature",
    "nature": "Environment/Nature",
    "technology": "Technology & Ethics",
    "artificial intelligence": "AI & Consciousness",
    "isolation": "Isolation",
    "loneliness": "Isolation",
    "exile": "Alienation",
    "colonialism": "Colonialism & Empire",
    "imperialism": "Colonialism & Empire",
    "betrayal": "Betrayal",
    "honour": "Honor",
    "jealousy": "Betrayal",
    "envy": "Betrayal"
}




def _canon_map(values, canon_list, synonym_map):
    out = []
    seen = set()
    for v in values or []:
        if not v: continue
        key = v.strip().lower()
        cand = synonym_map.get(key, v)
        norm = None
        for c in canon_list:
            if c.lower() == cand.lower():
                norm = c; break
        if not norm:
            norm = cand.title()
        low = norm.lower()
        if low not in seen:
            seen.add(low); out.append(norm)
    return out

def _strip_code_fences(s: str) -> str:
    s = str(s).strip()
    if s.startswith("```"):
        s = s.split("\n", 1)[1] if "\n" in s else ""
        if s.endswith("```"):
            s = s[:-3]
    return s.strip()

def _coerce_obj(v):
    if isinstance(v, dict): return v
    if isinstance(v, str):
        vv = _strip_code_fences(v)
        try:
            return json.loads(vv)
        except Exception:
            return None
    return None

def normalize_with_llm(consolidated: Dict[str,Any],
                       llm_provider: Optional[str]=None,
                       llm_model: Optional[str]=None,
                       config_path: Optional[str]=None) -> Dict[str,Any]:
    # Deterministic pre-normalization to reduce LLM work
    pre = dict(consolidated)  # shallow copy
    pre["genres"] = _canon_map(pre.get("genres", []), CANON_GENRES, GENRE_SYNONYMS)
    pre["themes"] = _canon_map(pre.get("themes", []), CANON_THEMES, THEME_SYNONYMS)
    pre["_raw"] = {
        "ol_subjects": pre.get("themes", []) + pre.get("genres", []),  # rough seed; real OL subjects already included above
    }

    # Pull out facts we do NOT let the LLM touch
    factual = {
        "primary_isbns": consolidated.get("primary_isbns", [])
    }

    prompt_template = """
You are a metadata librarian. Normalize the input to a strict JSON schema.

### Canonical Vocab
- GENRES (choose ALL that apply from this list when possible; if none fit, use []):
{canon_genres}
- THEMES (choose ALL that apply from this list when possible; if none fit, use []):
{canon_themes}

### Settings guidance
- Keep concrete places or time periods (e.g., "Saint Petersburg", "1860s").
- Remove vague/non-geographic items. Prefer City, Region/State, Country, Time Period.

### Series/Universe
- Keep exact names if real (e.g., "Harry Potter", "Discworld"). Drop marketing fluff.

### Awards
- Keep proper award names only (e.g., "Pulitzer Prize for Fiction"). Remove variants/duplicates.

### Themes note
- If explicit themes are missing, derive candidates from the provided description and OpenLibrary subjects,
  then map them to the canonical THEMES; drop anything that doesn’t fit.

### Output JSON schema (ONLY these fields)
{{
  "genres": string[],              // 0-12 items, Title Case, deduped
  "themes": string[],              // 0-20 items, Title Case, deduped
  "settings": string[],            // 0-20 items
  "associated_countries": string[],// 0-10 items
  "series_or_universe": string[],  // 0-10 items
  "awards": string[]               // 0-15 items
}}

### Important rules
- Select ALL applicable labels; do not force a single choice.
- If nothing fits a canonical list, return an empty array (not null).
- Do NOT invent facts. Deduplicate. Keep items concise (< 60 chars).
- Return ONLY JSON. No explanation.

### INPUT
{input_json}
"""

    prompt = PromptTemplate(
        input_variables=["canon_genres", "canon_themes", "input_json"],
        template=prompt_template
    )

    config = load_config(config_path=config_path) if config_path else load_config()
    llm = get_llm(llm_provider, llm_model, config, max_tokens=1200)

    runnable = prompt | llm
    out = runnable.invoke({
        "canon_genres": json.dumps(CANON_GENRES, ensure_ascii=False),
        "canon_themes": json.dumps(CANON_THEMES, ensure_ascii=False),
        "input_json": json.dumps(pre, ensure_ascii=False)
    })

    text = getattr(out, "content", out)
    clean_text = _strip_code_fences(str(text))

    normalized = None
    try:
        if 'extract_json' in globals():
            extracted = extract_json(clean_text)
            normalized = _coerce_obj(extracted)
        if normalized is None:
            normalized = _coerce_obj(clean_text)
    except Exception as e:
        logging.info("LLM JSON parse failed: %s", e)
        normalized = None

    # Fallback to deterministic pre-pass if LLM returns junk
    if not isinstance(normalized, dict):
        normalized = {
            "genres": pre["genres"][:12],
            "themes": pre["themes"][:20],
            "settings": pre.get("settings", [])[:20],
            "associated_countries": pre.get("associated_countries", [])[:10],
            "series_or_universe": pre.get("series_or_universe", [])[:10],
            "awards": pre.get("awards", [])[:15]
        }

    # Coerce nulls → arrays
    for k in ["genres","themes","settings","associated_countries","series_or_universe","awards"]:
        normalized[k] = normalized.get(k) or []

    # Merge back facts
    normalized["primary_isbns"] = factual["primary_isbns"]

    # Remove the temporary description if present in caller's structure after we return
    return normalized

# -----------------------
# Top-level function
# -----------------------
def get_story_metadata(story_json_path: str,
                       use_llm: bool=False,
                       llm_provider: Optional[str]=None,
                       llm_model: Optional[str]=None,
                       wikidata_mode: str="rest",
                       config_path: Optional[str]=None) -> Dict[str,Any]:

    with open(story_json_path, "r", encoding="utf-8") as f:
        story = json.load(f)

    title = _clean(story.get("title") or story.get("story_title"))
    author = _clean(story.get("author") or story.get("author_name"))
    year = _maybe_int_year(story.get("year") or story.get("publication_year"))

    if not title:
        raise ValueError("story_data.json missing 'title'")

    # 1) fetch
    ol = {}; ol_work = {}; gb = {}; wd = {}
    try:
        ol = fetch_openlibrary(title, author, year)
    except Exception as e:
        logging.info("OpenLibrary fetch failed: %s", e)

    # Work enrichment (if key present)
    try:
        ol_work = fetch_openlibrary_work(ol.get("openlibrary_key"))
    except Exception as e:
        logging.info("OpenLibrary Work enrichment failed: %s", e)

    try:
        gb = fetch_googlebooks(title, author)
    except Exception as e:
        logging.info("Google Books fetch failed: %s", e)

    try:
        if wikidata_mode == "off":
            wd = {}
            logging.info("WD: mode=off (skipping Wikidata)")
        else:
            wd = fetch_wikidata_rest(title, author)
            logging.info("WD: using Wikipedia→QID→REST path")
    except Exception as e:
        logging.info("Wikidata REST fetch failed: %s", e)
        wd = {}

    # 2) consolidate
    consolidated = consolidate(ol, ol_work, gb, wd)

    # 3) LLM normalize (optional)
    if use_llm:
        consolidated = normalize_with_llm(consolidated, llm_provider, llm_model, config_path=config_path)

    # Remove the temporary "description" field before persisting
    consolidated.pop("description", None)

    if consolidated == None:
        print("❌ ERROR: LLM failed to normalize metadata")
        raise ValueError("ERROR: LLM failed to normalize metadata")
    

    #overwrite some metadata field data with goodreads data if they exist --> goodreads better source of info
    goodreads_metadata = fetch_goodreads_metadata_by_title(title)
    
    #check if goodreads_metadata has any awards
    goodreads_awards = goodreads_metadata.get("work_details",{}).get("awards",[])
    if len(goodreads_awards) > 0:
        consolidated["awards"] = goodreads_awards
        print("✅ Goodreads Awards Metadata Added")

    #check if goodreads_metadata has any genres
    goodreads_genres = goodreads_metadata.get("genres",[])
    if len(goodreads_genres) > 0:
        consolidated["genres"] = goodreads_genres
        print("✅ Goodreads Genres Metadata Added")

    #check if goodreads_metadata has any setting
    goodreads_settings = goodreads_metadata.get("work_details",{}).get("setting",[])
    if len(goodreads_settings) > 0:
        consolidated["settings"] = goodreads_settings
        print("✅ Goodreads Setting Metadata Added")

    #check if goodreads_metadata has any characters 
    goodreads_characters = goodreads_metadata.get("work_details",{}).get("characters",[])
    if len(goodreads_characters) > 0:
        consolidated["characters"] = goodreads_characters
        print("✅ Goodreads Character Metadata Added")
    else:
        consolidated["characters"] = []


    #check


    # 4) write back into story_data.json under "metadata"
    story["metadata"] = consolidated
    with open(story_json_path, "w", encoding="utf-8") as f:
        json.dump(story, f, ensure_ascii=False, indent=2)

    return consolidated


#########################################
#########################################
### GOOODREADS METADATA #################
#########################################
#########################################

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


def fetch_goodreads_metadata_by_title(title) -> Optional[Dict[str, Any]]:
   
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

   
    genres = _extract_genres(bs)

    # ids + metadata
    data: Dict[str, Any] = {
        "page_url": book_url,
    }

    data.update(_extract_ids_from_url(book_url))
    data.update(_extract_ids_from_dom(bs))


    ids = _extract_isbn_asin(bs)
    if ids:
        data.update(ids)                  # e.g., isbn13 / isbn10 / asin at top-level
        data.setdefault("edition", {}).update(ids)  # also nested if you prefer grouping
    
    work_details = _extract_work_details(bs)
    if work_details:
        data.setdefault("work_details", {}).update(work_details)

    # genres (top-level list of names)
    
    if genres:
        data["genres"] = genres

    #4 metadata fields from goodreads
    # genres
    # work_details
    #   setting
    #   characters
    #   awards

    print(data)
    return data


#story_book_cover
#story_metadata
#st

# --- Example ---




# test_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/story_data/crime-and-punishment-rodion-raskolnikov.json"
# get_story_cover(test_path)


# fetch_goodreads_metadata_by_title("Harry Potter and the Sorcerer's Stone")


# story_metadata_llm_provider = "google"
# story_metadata_llm_model = "gemini-2.5-pro"
# get_story_metadata(
#     story_json_path="/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/story_data/crime-and-punishment-rodion-raskolnikov.json",
#     use_llm="on",
#     config_path=PATHS['config'],
#     llm_provider=story_metadata_llm_provider,
#     llm_model=story_metadata_llm_model
# )
# print("✅ Story MetaData")
# print("")


   
