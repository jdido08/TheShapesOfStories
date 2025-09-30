# extract_story_metadata.py

from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
import json
from langchain.prompts import PromptTemplate
from llm import load_config, get_llm, extract_json

# ----------------------------
# Controlled Vocabulary
# ----------------------------

TAXONOMY = {
    "genres": {
        "fiction": [
           # "Literary Fiction",
            "Historical Fiction",
            "Romance",
            "Mystery & Crime",
            "Thriller & Suspense",
            "Horror",
            "Science Fiction",
            "Fantasy",
            "Adventure",
            "Western",
            "War/Military Fiction",
            "Satire/Humor"
        ],
        "nonfiction": [
            "Biography",
            "Autobiography",
            "Memoir",
            "History",
            "True Crime",
            "Science & Nature",
            "Travel & Exploration",
            "Journalism/Reportage",
            "Politics & Current Affairs",
            "Business & Economics",
            "Sports Writing",
            "Philosophy & Ideas"
        ]
    },
    "subgenres_by_genre": {
        # "Literary Fiction": [
        #     "Coming-of-Age (Bildungsroman)",
        #     "Family Saga",
        #     "Social Realism",
        #     "Metafiction/Experimental",
        #     "Campus Novel",
        #     "Domestic Drama",
        #     "Workplace/Professional Life"
        # ],
        "Historical Fiction": [
            "Ancient World",
            "Medieval",
            "Renaissance/Early Modern",
            "18th Century",
            "19th Century",
            "Early 20th (1900–1945)",
            "Mid 20th (1946–1979)",
            "Late 20th (1980–1999)",
            "WWI",
            "WWII",
            "American Civil War",
            "Colonial/Postcolonial"
        ],
        "Romance": [
            "Contemporary Romance",
            "Historical Romance",
            "Regency Romance",
            "Paranormal Romance",
            "Gothic Romance",
            "Romantic Suspense",
            "Inspirational/Clean Romance",
            "LGBTQ+ Romance"
        ],
        "Mystery & Crime": [
            "Detective/Private Eye",
            "Police Procedural",
            "Cozy/Amateur Sleuth",
            "Noir/Hardboiled",
            "Heist/Caper",
            "Forensic Mystery",
            "Legal Mystery",
            "Historical Mystery"
        ],
        "Thriller & Suspense": [
            "Psychological Thriller",
            "Domestic Thriller",
            "Political Thriller",
            "Espionage/Spy",
            "Action Thriller",
            "Techno-Thriller",
            "Medical Thriller",
            "Legal Thriller"
        ],
        "Horror": [
            "Gothic Horror",
            "Supernatural/Occult",
            "Cosmic Horror",
            "Folk Horror",
            "Psychological Horror",
            "Monster/Creature",
            "Haunted House",
            "Extreme/Splatterpunk"
        ],
        "Science Fiction": [
            "Hard SF",
            "Social/Soft SF",
            "Space Opera",
            "Cyberpunk",
            "Biopunk",
            "Steampunk",
            "Time Travel",
            "Alternate History",
            "Dystopian",
            "Post-Apocalyptic",
            "First Contact",
            "Military SF",
            "Climate Fiction (Cli-Fi)"
        ],
        "Fantasy": [
            "High/Epic Fantasy",
            "Low Fantasy",
            "Urban Fantasy",
            "Dark Fantasy",
            "Sword & Sorcery",
            "Portal Fantasy",
            "Historical Fantasy",
            "Fairy Tale Retelling",
            "Grimdark",
            "Mythic/Legendary",
            "Gaslamp Fantasy",
            "Paranormal/Occult Fantasy"
        ],
        "Adventure": [
            "Survival",
            "Exploration",
            "Nautical/Seafaring",
            "Swashbuckler",
            "Lost World",
            "Desert/Jungle Expedition"
        ],
        "Western": [
            "Classic Western",
            "Revisionist Western",
            "Outlaw/Heist Western",
            "Frontier Romance",
            "Weird Western"
        ],
        "War/Military Fiction": [
            "Infantry/Frontline",
            "Naval Warfare",
            "Air Warfare",
            "Special Operations",
            "Home Front",
            "Military Alternate History"
        ],
        "Satire/Humor": [
            "Satire",
            "Parody",
            "Comic Novel",
            "Picaresque"
        ],
        "Biography": [
            "Political Biography",
            "Literary/Artistic Biography",
            "Scientific/Tech Biography",
            "Business Biography",
            "Sports Biography",
            "Military Biography"
        ],
        "Autobiography": [
            "Political Autobiography",
            "Literary/Artistic Autobiography",
            "Scientific/Tech Autobiography",
            "Business Autobiography",
            "Sports Autobiography",
            "Military Autobiography"
        ],
        "Memoir": [
            "Childhood/Coming-of-Age Memoir",
            "Travel Memoir",
            "Illness/Medical Memoir",
            "Addiction/Recovery Memoir",
            "Grief/Bereavement Memoir",
            "Spiritual Memoir"
        ],
        "History": [
            "Military History",
            "Cultural History",
            "Social History",
            "Economic History",
            "Microhistory",
            "Urban/Local History"
        ],
        "True Crime": [
            "Investigative True Crime",
            "Courtroom/Trial",
            "Organized Crime",
            "Serial Crime",
            "White-Collar Crime"
        ],
        "Science & Nature": [
            "Popular Science",
            "Natural History",
            "Environmental Writing",
            "History of Science",
            "Astronomy/Space",
            "Life Sciences"
        ],
        "Travel & Exploration": [
            "Travelogue",
            "Expedition/Adventure",
            "Place-Based Essays",
            "Pilgrimage/Journey"
        ],
        "Journalism/Reportage": [
            "Longform Investigative",
            "War Correspondence",
            "Immersive/Participatory",
            "Profile Collection"
        ],
        "Politics & Current Affairs": [
            "Policy Analysis",
            "Political Narrative",
            "Elections/Campaigns",
            "Geopolitics"
        ],
        "Business & Economics": [
            "Company Profile",
            "Market/Tech History",
            "Management/Leadership Narrative",
            "Behavioral Economics (Narrative)"
        ],
        "Sports Writing": [
            "Season Chronicle",
            "Athlete Profile",
            "Team History",
            "Game/Event Narrative"
        ],
        "Philosophy & Ideas": [
            "Intellectual History",
            "Popular Philosophy",
            "Ethics & Society",
            "Science & Ideas Crossover"
        ]
    },
    "normalize_genre": {
        "Sci-Fi": "Science Fiction",
        "SF": "Science Fiction",
        "Speculative Fiction": "Science Fiction",
        "SFF": "Fantasy",
        "Rom-Com": "Romance",
        "Crime": "Mystery & Crime",
        "Suspense": "Thriller & Suspense",
        "Humour": "Satire/Humor",
        "War": "War/Military Fiction",
        "Military": "War/Military Fiction",
        "Reportage": "Journalism/Reportage",
        "Current Affairs": "Politics & Current Affairs",
        "Business": "Business & Economics"
    },
    "normalize_subgenre": {
        "Bildungsroman": "Coming-of-Age (Bildungsroman)",
        "Hardboiled": "Noir/Hardboiled",
        "Cozy": "Cozy/Amateur Sleuth",
        "Legal": "Legal Thriller",
        "Medical": "Medical Thriller",
        "Spy": "Espionage/Spy",
        "Gaslamp": "Gaslamp Fantasy",
        "Grim Dark": "Grimdark",
        "Cli Fi": "Climate Fiction (Cli-Fi)"
    },
    "heritage": ["Classic", "Modern Classic", "Contemporary", "Cult Classic"]

}


SETTING_TAXONOMY = {
  # Named places remain free-text ("setting_city/region/country") but are normalized.
  # These facets are strictly controlled for collection building:
  "place_types": [
    # urban units
    "City","Town","Village","Neighborhood","Street","House","Apartment","Estate/Manor","Castle/Fort",
    # civic/institutional
    "School/University","Library","Hospital/Asylum","Prison/Jail","Courtroom","Police Station",
    "Government/Palace","Museum/Gallery","Theater/Cinema","Hotel/Inn","Bar/Tavern","Restaurant","Shop/Market",
    "Office/Corporate HQ","Laboratory","Factory/Mill","Mine","Farm/Ranch","Warehouse","Research Station",
    # transport nodes/vehicles
    "Harbor/Dock","Ship","Submarine","Sea Platform","Train","Train Station",
    "Airplane","Airport","Road/Highway","Car/Bus",
    # outdoor & landforms
    "Coast","Beach","Island","Archipelago","Desert","Forest","Jungle","Mountain","Valley","Plain/Steppe",
    "Cave/Underground","Wetland/Swamp","River","Lake","Waterfall","Glacier/Icefield",
    # seas & beyond
    "Sea","Ocean","Polar Region","Outer Space","Spacecraft","Space Station","Planet","Moon","Asteroid",
    # metaphysical/virtual
    "Afterlife/Otherworld","Dreamscape","Virtual/Simulated World"
  ],
  "environment_tags": [
    "Urban","Suburban","Rural","Wilderness",
    "Coastal","Island","Riverine","Lacustrine","Wetland","Open Ocean","Underwater",
    "Desert","Savanna/Grassland","Temperate Forest","Boreal Forest","Tropical Rainforest",
    "Mountain/Alpine","Arctic/Polar","Underground","Outer Space","Industrial","Institutional","Domestic"
  ],
  "macroregions": [  # UN-ish macro areas, for browsing
    "North America","Latin America & Caribbean","Western Europe","Eastern Europe","Middle East & North Africa",
    "Sub-Saharan Africa","South Asia","East Asia","Southeast Asia","Oceania","Russia & CIS","Polar Regions",
    "Extraterrestrial","Global/Multinational"
  ],
  "mobility_modes": [
    "Sea Voyage","River Voyage","Road Trip","Train Journey","Air Travel","Space Voyage",
    "Foot Journey/Trek","Migration/Exodus","Pilgrimage","Siege/Encampment","Stationary/Local"
  ],
  "time_window_labels": [
    "One day","One night","A weekend","A season","One year","Multiple years","Multiple decades","Entire lifetime"
  ],
  "era_labels_global": [
    "Ancient","Medieval","Early Modern","18th Century",
    "Early 19th Century","Mid 19th Century","Late 19th Century",
    "Early 20th (1900–1945)","Mid 20th (1946–1979)","Late 20th (1980–1999)","21st Century"
  ],
  "era_labels_regional": {
    "United Kingdom": ["Regency","Victorian","Edwardian","Interwar","Postwar"],
    "United States": ["Gilded Age","Progressive Era","Jazz Age","Great Depression","WWII","Cold War","Civil Rights Era","Information Age"],
    "Japan": ["Edo","Meiji","Taishō","Shōwa","Heisei","Reiwa"],
    "China": ["Ming","Qing","Republican Era","PRC"],
    "India": ["Mughal","British Raj","Post-Independence"]
  },
  "normalize_toponym": {
    "NYC":"New York City","New York, NY":"New York City","LA":"Los Angeles","SF":"San Francisco",
    "Bombay":"Mumbai","Peking":"Beijing","Saigon":"Ho Chi Minh City","Petersburg":"Saint Petersburg"
  }
}


# ----------------------------
# Helpers & Validation
# ----------------------------

def _flatten_genres() -> List[str]:
    return TAXONOMY["genres"]["fiction"] + TAXONOMY["genres"]["nonfiction"]


def validate_genres_subgenres(genres: Optional[List[str]], subgenres: Optional[List[str]]) -> Tuple[Optional[List[str]], Optional[List[str]]]:
    """Enforce allowed vocab: ≤2 genres, ≤3 subgenres per selected genre (max 6 total)."""
    if not genres:
        return None, None
    allowed_genres = set(_flatten_genres())
    g_clean = [g for g in genres if g in allowed_genres][:2]
    if not g_clean:
        return None, None
    # Build subgenres up to 3 per selected genre, preserving input order and de-duping
    s_clean: List[str] = []
    if subgenres:
        for g in g_clean:
            allowed_subs = TAXONOMY["subgenres_by_genre"].get(g, [])
            count_for_g = 0
            for s in subgenres:
                if s in allowed_subs and s not in s_clean:
                    s_clean.append(s)
                    count_for_g += 1
                    if count_for_g >= 3:
                        break
    return g_clean or None, (s_clean or None)


def validate_setting_facets(data: Dict[str, Any]) -> Dict[str, Any]:
    def pick(vals, allowed, cap=None):
        if not vals: return None
        keep = []
        for v in vals:
            if v in allowed and v not in keep:
                keep.append(v)
                if cap and len(keep) >= cap: break
        return keep or None

    data["place_types"] = pick(data.get("place_types"), SETTING_TAXONOMY["place_types"], cap=3)
    data["environment"] = pick(data.get("environment"), SETTING_TAXONOMY["environment_tags"], cap=3)
    data["macroregion"] = pick(data.get("macroregion"), SETTING_TAXONOMY["macroregions"], cap=2)
    data["mobility"]    = pick(data.get("mobility"), SETTING_TAXONOMY["mobility_modes"], cap=2)

    if data.get("time_window") not in SETTING_TAXONOMY["time_window_labels"]:
        data["time_window"] = None

    # era: allow controlled labels or freeform decades/centuries
    allowed_eras = set(SETTING_TAXONOMY["era_labels_global"])
    for eras in SETTING_TAXONOMY["era_labels_regional"].values():
        allowed_eras.update(eras)
    era = data.get("setting_era")
    if era and (era not in allowed_eras) and not any(ch.isdigit() for ch in era):
        data["setting_era"] = None
    return data


def normalize_toponyms(data: Dict[str, Any]) -> Dict[str, Any]:
    alias = SETTING_TAXONOMY.get("normalize_toponym", {})
    def norm_list(vals):
        if not vals: return None
        out = []
        for v in vals:
            v2 = alias.get(v, v)
            if v2 not in out:
                out.append(v2)
        return out or None

    for key in ("setting_city", "setting_region", "setting_country"):
        data[key] = norm_list(data.get(key))
    return data


def normalize_genre_output(result: Dict[str, Any]) -> Dict[str, Any]:
    if result.get("genre"):
        result["genre"] = [TAXONOMY["normalize_genre"].get(g, g) for g in result["genre"]]
    if result.get("subgenre"):
        result["subgenre"] = [TAXONOMY["normalize_subgenre"].get(s, s) for s in result["subgenre"]]
    return result



def _coerce_to_text(msg: Any) -> str:
    """
    Turn various LangChain/OpenAI message shapes into a plain string.
    Handles:
      - AIMessage(content="...")
      - AIMessage(content=[{"type":"text","text":"..."} , ...])
      - plain strings
    """
    # LangChain AIMessage or similar
    content = getattr(msg, "content", msg)

    # Already a string
    if isinstance(content, str):
        return content

    # Newer SDKs sometimes return a list of content parts
    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict):
                # OpenAI-style content parts
                if part.get("type") == "text" and isinstance(part.get("text"), str):
                    parts.append(part["text"])
                elif "text" in part and isinstance(part["text"], str):
                    parts.append(part["text"])
            elif isinstance(part, str):
                parts.append(part)
        return "\n".join(p for p in parts if p)

    # Last resort
    return "" if content is None else str(content)

def validate_heritage(h: Optional[str]) -> Optional[str]:
    if h in TAXONOMY["heritage"]:
        return h
    return None



# ----------------------------
# Prompt A — Setting Extractor
# ----------------------------

SETTING_PROMPT_TEMPLATE = """SYSTEM
You are a meticulous bibliographic cataloger. Your job is to extract SETTING facets using a strict, controlled vocabulary.
If a candidate value is not in the supplied taxonomy, you must return null for that field (or exclude the value).
When in doubt, be conservative and return fewer labels.

TAXONOMY (for controlled facets only)
{{ setting_taxonomy_json }}

CONTEXT
<title>{{ title }}</title>
<author>{{ author }}</author>
<publication_year>{{ publication_year }}</publication_year>
<summary>{{ summary }}</summary>

GUIDING PRINCIPLES
- Focus on what is explicitly stated or canonically uncontested about setting (place/time), not themes or vibes.
- Prefer canonical/modern toponyms (e.g., "Mumbai" not "Bombay") unless the historical name is essential; if both are salient, include both with modern first.
- Choose specific and *salient* facets. Do not over-list.
- City/Region/Country are free-text lists (later normalized). All other facets MUST come from the taxonomy.

OUTPUT REQUIREMENTS
Return ONLY JSON with these fields:

{
  "setting_city":    ["New York City", "Long Island"] | null,         // free-text list, deduped, ≤5 items total
  "setting_region":  ["New York State", "Northeast"] | null,          // free-text list, deduped, ≤5 items total
  "setting_country": ["United States"] | null,                         // free-text list, deduped, ≤3 items total

  "macroregion": ["Western Europe", "North America"] | null,          // from taxonomy; ≤2
  "place_types": ["City", "Bar/Tavern", "Apartment"] | null,          // from taxonomy; ≤3; pick the *most* characteristic
  "environment": ["Urban", "Coastal"] | null,                         // from taxonomy; ≤3
  "mobility": ["Road Trip", "Stationary/Local"] | null,               // from taxonomy; ≤2 or null if not salient

  "setting_time": "One summer in the 1920s" | null,                   // short human phrase (≤70 chars). Do NOT invent plot.
  "time_window": "One year" | "Multiple years" | null,                // from taxonomy time_window_labels OR null
  "setting_era": "Early 20th (1900–1945)" | "Victorian" | "1990s" | null, // prefer taxonomy era labels; otherwise a specific decade/century string

  "evidence": {
    "place":   { "from": "summary|world", "note": "Quoted or paraphrased details that justify city/region/country." } | null,
    "facet":   { "from": "summary|world", "note": "Why chosen place_types/environment/mobility/macroregion." } | null,
    "time":    { "from": "summary|world", "note": "Why chosen time_window/era/setting_time." } | null
  },

  "confidence": {
    "place": 0.0-1.0 | null,
    "facet": 0.0-1.0 | null,
    "time":  0.0-1.0 | null,
    "_overall": 0.0-1.0
  },

  "notes": "Brief edge-case comment (≤140 chars) or empty string"
}

SELECTION RULES (STRICT)
1) Counts:
   - setting_city + setting_region + setting_country combined ≤ 8 items (drop the least salient if over).
   - macroregion ≤ 2; place_types ≤ 3; environment ≤ 3; mobility ≤ 2.

2) Place picking:
   - Include specific named locales only if they are central (scenes occur there), not mere mentions.
   - If the story spans many locales, choose the 2–4 most narratively significant.

3) Time selection:
   - If the time span is explicit, map to one value of time_window; otherwise null.
   - For setting_era, prefer a taxonomy label that matches the geography; otherwise a precise decade (e.g., "1990s") or century.
   - setting_time is a short natural-language phrase summarizing timeframe (optional).

4) Normalization:
   - Use modern canonical toponyms when possible. If a historical name is crucial, include both: "Mumbai (Bombay)".

VALIDATION
- If any controlled facet contains a label not in the taxonomy, return null for that facet.
- If evidence is weak, lower confidence. If absent, prefer nulls.

OUTPUT
Return ONLY the JSON object above. No prose, no explanations."""


def extract_setting_metadata(
    config_path: str,
    title: str,
    author: str,
    publication_year: int,
    summary: str,
    llm_provider: str,
    llm_model: str,
    max_tokens: int = 8192
) -> Dict[str, Any]:
    prompt = PromptTemplate(
        input_variables=["title","author","publication_year","summary","setting_taxonomy_json"],
        template=SETTING_PROMPT_TEMPLATE,
        template_format="jinja2",            # ← important
    )
    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=max_tokens)
    runnable = prompt | llm
    output = runnable.invoke({
        "title": title,
        "author": author,
        "publication_year": publication_year,
        "summary": summary,
        "setting_taxonomy_json": json.dumps(SETTING_TAXONOMY, ensure_ascii=False),

    })
    print("OUTPUT")
    print(output)
    output_text = _coerce_to_text(output)
    print("OUTPUT TEXT")
    print(output_text)
    extracted_text = extract_json(output_text)
    print("EXTRACTED TEXT")
    print(extracted_text)
    try:
        data = json.loads(extracted_text)
        data = validate_setting_facets(data)
        data = normalize_toponyms(data)     # <- add this
        return data
    except Exception:
        return {"error": "Failed to parse setting metadata JSON", "raw": output_text}


# ------------------------------------------
# Prompt B — Genre/Subgenre Classifier
# ------------------------------------------

GENRE_PROMPT_TEMPLATE = """SYSTEM
You classify books using a strict taxonomy. If a label isn’t in TAXONOMY, return null.

TAXONOMY
{{taxonomy_json}}

CONTEXT
<title>{{title}}</title>
<author>{{author}}</author>
<publication_year>{{publication_year}}</publication_year>
<summary>{{summary}}</summary>

RULES
- Normalize candidate labels using normalization_map, then select.
- ≤2 genres total; ≤3 subgenres per selected genre.
- Mystery vs Thriller: puzzle/investigation → Mystery; imminent danger/clock → Thriller.
- Dystopian/Post-Apocalyptic → Science Fiction.
- Magical Realism → Fantasy. If marketed as “literary,” note that in `notes` (do not add as a genre).

OUTPUT (JSON only)
{
  "genre":    ["Top-level genre", "Optional second genre"] | null,
  "subgenre": ["Subgenre 1","Subgenre 2","Subgenre 3"] | null,
  "evidence": {
    "genre":    { "from": "summary|normalization|world", "note": "…" } | null,
    "subgenre": { "from": "summary|normalization|world", "note": "…" } | null
  },
  "confidence": {
    "genre": 0.0-1.0 | null,
    "subgenre": 0.0-1.0 | null,
    "_overall": 0.0-1.0
  },
  "notes": "Brief edge-case comment if needed; else \"\""
}
"""

def classify_genre_subgenre(
    config_path: str,
    title: str,
    author: str,
    publication_year: int,
    summary: str,
    llm_provider: str,
    llm_model: str,
    max_tokens: int = 8192
) -> Dict[str, Any]:
    taxonomy_json = json.dumps(TAXONOMY, ensure_ascii=False)

    prompt = PromptTemplate(
        input_variables=["title", "author", "publication_year", "summary", "taxonomy_json"],
        template=GENRE_PROMPT_TEMPLATE,
        template_format="jinja2",
    )
    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=max_tokens)
    runnable = prompt | llm
    output = runnable.invoke({
        "title": title,
        "author": author,
        "publication_year": publication_year,
        "summary": summary,
        "taxonomy_json": taxonomy_json,
    })
    output_text = getattr(output, "content", output)
    extracted_text = extract_json(output_text)
    try:
        result = json.loads(extracted_text)
        result = normalize_genre_output(result)
    except Exception:
        return {"error": "Failed to parse genre JSON", "raw": output_text}

    g, s = validate_genres_subgenres(result.get("genre"), result.get("subgenre"))
    result["genre"] = g
    result["subgenre"] = s
    result["heritage"] = validate_heritage(result.get("heritage"))

    return result

# ----------------------------------------------
# Prompt C — Publication Facts (lang/pub/awards)
# ----------------------------------------------

PUBLICATION_PROMPT_TEMPLATE = """SYSTEM
You return publication facts for the specific work. Be conservative: if not ≥0.70 confident, use null (or [] for awards).

CONTEXT
<title>{{title}}</title>
<author>{{author}}</author>
<publication_year>{{publication_year}}</publication_year>
<summary>{{summary}}</summary>

RULES
- Language/publication_country: use original first-publication details.
- Awards: wins for THIS WORK only (no nominations; no lifetime/author awards).

OUTPUT (JSON only)
{
  "language": "Original language" | null,
  "publication_country": "Country of first publication" | null,
  "awards": [
    { "name": "Award Name", "year": 19XX, "category": "Category or null" }
  ]
}
"""

def extract_publication_facts(
    config_path: str,
    title: str,
    author: str,
    publication_year: int,
    summary: str,
    llm_provider: str,
    llm_model: str,
    max_tokens: int = 8192
) -> Dict[str, Any]:
    # template = PUBLICATION_PROMPT_TEMPLATE.format(
    #     title=title,
    #     author=author,
    #     publication_year=publication_year,
    #     summary=summary
    # )
    prompt = PromptTemplate(
        input_variables=["title", "author", "publication_year", "summary"],
        template=PUBLICATION_PROMPT_TEMPLATE,
        template_format="jinja2",
    )
    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=max_tokens)
    runnable = prompt | llm
    output = runnable.invoke({
        "title": title,
        "author": author,
        "publication_year": publication_year,
        "summary": summary
    })
    output_text = getattr(output, "content", output)
    extracted_text = extract_json(output_text)
    try:
        data = json.loads(extracted_text)
        # Normalize awards field to list
        if not isinstance(data.get("awards", []), list):
            data["awards"] = []
        return data
    except Exception:
        return {"error": "Failed to parse publication facts JSON", "raw": output_text}



# ----------------------------------------------
# Prompt D — Series & Universe (independent)
# ----------------------------------------------

SERIES_UNIVERSE_PROMPT_TEMPLATE = """SYSTEM
You identify whether a work belongs to a named SERIES and/or a named SHARED UNIVERSE.
Return null unless ≥0.80 confident. Avoid hallucinations.

CONTEXT
<title>{{ title }}</title>
<author>{{ author }}</author>
<publication_year>{{ publication_year }}</publication_year>
<summary>{{ summary }}</summary>

RULES
- Accept only if explicitly signaled in the summary OR famous, uncontested facts (e.g., "Harry Potter" series, "Marvel" universe).
- Do not infer from character overlap unless the series/universe name is canonical.
- If part of a numbered series, output the canonical series umbrella name (e.g., "A Song of Ice and Fire").
- Shared universe examples: "Marvel", "DC", "Star Wars", "Star Trek", "Wizarding World", "Cosmere", "Middle-earth", "Discworld", etc.
- If neither series nor universe is clearly applicable at ≥0.80 confidence, return both as null.

OUTPUT (JSON only)
{
  "series": "Series name" | null,
  "universe": "Shared universe name" | null,
  "evidence": {
    "series":   { "from": "summary|world", "note": "…" } | null,
    "universe": { "from": "summary|world", "note": "…" } | null
  },
  "confidence": {
    "series": 0.0-1.0 | null,
    "universe": 0.0-1.0 | null,
    "_overall": 0.0-1.0
  }
}
"""


def extract_series_universe(
    config_path: str,
    title: str,
    author: str,
    publication_year: int,
    summary: str,
    llm_provider: str,
    llm_model: str,
    max_tokens: int = 8192
) -> Dict[str, Any]:
    prompt = PromptTemplate(
        input_variables=["title", "author", "publication_year", "summary"],
        template=SERIES_UNIVERSE_PROMPT_TEMPLATE,
        template_format="jinja2",
    )
    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=max_tokens)
    runnable = prompt | llm
    output = runnable.invoke({
        "title": title,
        "author": author,
        "publication_year": publication_year,
        "summary": summary
    })
    output_text = getattr(output, "content", output)
    extracted_text = extract_json(output_text)
    try:
        data = json.loads(extracted_text)
        return data
    except Exception:
        return {"error": "Failed to parse series/universe JSON", "raw": output_text}

# ----------------------------
# Orchestrator (optional)
# ----------------------------

@dataclass
class StoryInput:
    title: str
    author: str
    publication_year: int
    summary: str

def extract_story_metadata_all(
    config_path: str,
    story: StoryInput,
    llm_provider: str,
    llm_model: str
) -> Dict[str, Any]:
    """Run A and B in sequence (you may run them in parallel in your infra), then C."""
    A = extract_setting_metadata(
        config_path=config_path,
        title=story.title,
        author=story.author,
        publication_year=story.publication_year,
        summary=story.summary,
        llm_provider=llm_provider,
        llm_model=llm_model
    )

    print(A)

    B = classify_genre_subgenre(
        config_path=config_path,
        title=story.title,
        author=story.author,
        publication_year=story.publication_year,
        summary=story.summary,
        llm_provider=llm_provider,
        llm_model=llm_model
    )
    C = extract_publication_facts(
        config_path=config_path,
        title=story.title,
        author=story.author,
        publication_year=story.publication_year,
        summary=story.summary,
        llm_provider=llm_provider,
        llm_model=llm_model
    )

    D = extract_series_universe(
        config_path=config_path,
        title=story.title,
        author=story.author,
        publication_year=story.publication_year,
        summary=story.summary,
        llm_provider=llm_provider,
        llm_model=llm_model
    )
    # Precedence: explicit hints > LLM extraction > None
    series_value = (D.get("series") if isinstance(D, dict) else None)
    universe_value = (D.get("universe") if isinstance(D, dict) else None)

    result = {
        "title": story.title,
        "author": story.author,
        "publication_year": story.publication_year,
        "metadata": {
            "setting_city":    A.get("setting_city"),
            "setting_region":  A.get("setting_region"),
            "setting_country": A.get("setting_country"),
            "setting_era":     A.get("setting_era"),
            "setting_time":    A.get("setting_time"),
            "place_types":     A.get("place_types"),
            "environment":     A.get("environment"),
            "macroregion":     A.get("macroregion"),
            "mobility":        A.get("mobility"),
            "time_window":     A.get("time_window"),
            "genre":           B.get("genre"),
            "subgenre":        B.get("subgenre"),
            "heritage":        B.get("heritage"),
            "series":          series_value,
            "universe":        universe_value,
            "awards":          C.get("awards", []),
            "publication_country": C.get("publication_country"),
            "language":        C.get("language")
        },
        "evidence": {
            **(A.get("evidence") or {}),
            "genre":    (B.get("evidence") or {}).get("genre"),
            "subgenre": (B.get("evidence") or {}).get("subgenre"),
            "heritage": (B.get("evidence") or {}).get("heritage"),
        },
        "confidence": {
            "setting_city":    (A.get("confidence") or {}).get("setting_city"),
            "setting_region":  (A.get("confidence") or {}).get("setting_region"),
            "setting_country": (A.get("confidence") or {}).get("setting_country"),
            "setting_era":     (A.get("confidence") or {}).get("setting_era"),
            "setting_time":    (A.get("confidence") or {}).get("setting_time"),
            "place_types": (A.get("confidence") or {}).get("place_types"),
            "environment": (A.get("confidence") or {}).get("environment"),
            "macroregion": (A.get("confidence") or {}).get("macroregion"),
            "mobility":    (A.get("confidence") or {}).get("mobility"),
            "time_window": (A.get("confidence") or {}).get("time_window"),
            "genre":           (B.get("confidence") or {}).get("genre"),
            "subgenre":        (B.get("confidence") or {}).get("subgenre"),
            "heritage":  (B.get("confidence") or {}).get("heritage"),
            "_overall":        None
        },
        "notes": B.get("notes") or ""
    }
    return result



### FUNCTIONS TO CALL EXTRACTING STORY METADATA ##


# # Fields I know
# - Printify Product ID
# - Shape Archetype
# - Shape Symbols
# - Font Family
# - Medium
# - Line Type
# - Author
# - Character / Protagonist
# - Story Title

# # Fields I can derive
# - Font Color Name
# - Background Color Name
# - Font Color (Hex)
# - Background Color (Hex)
# - Color (Background/Front Color Combo) ---> NEED TO ADD 
# - Story Slug

## TAGS
# # Field I need LLM 
# - Setting Region
# - Setting Country
# - Language
# - Awards
# - Setting Era
# - Setting Time
# - Setting City
# - Subgenre
# - Publication Year (I might have this )
# - Publication Country
# - Genre
# - Series
# - Universe

# Why have tags?
# to create things like:
# The Shapes of [City/Region/Country] e.g. The Shapes of Pittsburgh
# The Shapes of [Genre]               e.g. The Shapes of Sci-Fi, Fantasy
# The Shapes of [Theme]               e.g. The Shapes of Love 
# The Shapes of [Setting]             e.g. The Shapes of WWII
# The Shapes of [Country]             e.g. The Shapes of Russian Literature


#Maybe
# openlib
#   - publishing
#       - first_publish_year
#   - physical_dimensions
#        - number_of_pages_median
#   - subjects_and_characters
#       - subjects
#       - subject_places
#       - subject_times
#   - excerpts
#   - covers
#   - ratings_and_reviews
#   - first_sentence


from pathlib import Path
import json

def get_story_metdata(config_path, story_data_path, llm_provider, llm_model):
    path = Path(story_data_path)
    story_data = json.loads(path.read_text(encoding="utf-8"))
    story_input = StoryInput(
        title=story_data["title"],
        author=story_data["author"],
        publication_year=int(story_data["year"]),
        summary=story_data["summary"]
    )
    story_metadata = extract_story_metadata_all(config_path, story_input, llm_provider, llm_model)

    story_data["story_metadata"] = story_metadata["metadata"]
    story_data["story_metadata_evidence"] = story_metadata["evidence"]
    story_data["story_metadata_confidence"] = story_metadata["confidence"]

    path.write_text(json.dumps(story_data, ensure_ascii=False, indent=2), encoding="utf-8")
