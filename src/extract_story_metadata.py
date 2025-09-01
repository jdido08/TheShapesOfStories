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


# ----------------------------
# Prompt A — Setting Extractor
# ----------------------------

SETTING_PROMPT_TEMPLATE = """SYSTEM
You extract setting metadata from book descriptions. If not ≥0.60 confident, return null.

CONTEXT
<title>{{ title }}</title>
<author>{{ author }}</author>
<publication_year>{{ publication_year }}</publication_year>
<summary>{{ summary }}</summary>

RULES
- Use both the summary and world knowledge to resolve place/time details. When they conflict, prefer well-established canon; note any conflict briefly in `notes`.
- Prefer modern toponyms unless the historical name is essential to the text.
- Order arrays by prominence/page time.

OUTPUT (JSON only)
{
  "setting_city":    ["City 1","City 2"] | null,
  "setting_region":  ["State/Province/Region 1"] | null,
  "setting_country": ["Country 1"] | null,
  "setting_era":     "Era label or decade/century" | null,
  "setting_time":    "Season/day/time-window" | null,
  "evidence": {
    "setting_city":    { "from": "summary|world", "note": "…" } | null,
    "setting_region":  { "from": "summary|world", "note": "…" } | null,
    "setting_country": { "from": "summary|world", "note": "…" } | null,
    "setting_era":     { "from": "summary|world", "note": "…" } | null,
    "setting_time":    { "from": "summary|world", "note": "…" } | null
  },
  "confidence": {
    "setting_city": 0.0-1.0 | null,
    "setting_region": 0.0-1.0 | null,
    "setting_country": 0.0-1.0 | null,
    "setting_era": 0.0-1.0 | null,
    "setting_time": 0.0-1.0 | null,
    "_overall": 0.0-1.0
  }
}
"""

def extract_setting_metadata(
    config_path: str,
    title: str,
    author: str,
    publication_year: int,
    summary: str,
    llm_provider: str,
    llm_model: str,
    max_tokens: int = 1800
) -> Dict[str, Any]:
    prompt = PromptTemplate(
        input_variables=["title", "author", "publication_year", "summary"],
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
        "summary": summary
    })
    output_text = getattr(output, "content", output)
    extracted_text = extract_json(output_text)
    try:
        return json.loads(extracted_text)
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
- Magical Realism → Fantasy by default; if clearly marketed as Literary Fiction, keep Literary and note why.

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
    max_tokens: int = 1800
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
    except Exception:
        return {"error": "Failed to parse genre JSON", "raw": output_text}

    g, s = validate_genres_subgenres(result.get("genre"), result.get("subgenre"))
    result["genre"] = g
    result["subgenre"] = s
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
    max_tokens: int = 1400
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
<title>{title}</title>
<author>{author}</author>
<publication_year>{publication_year}</publication_year>
<summary>{summary}</summary>

RULES
- Accept only if explicitly signaled in the summary OR famous, uncontested facts (e.g., "Harry Potter" series, "Marvel" universe).
- Do not infer from character overlap unless the series/universe name is canonical.
- If part of a numbered series, output the canonical series umbrella name (e.g., "A Song of Ice and Fire").
- Shared universe examples: "Marvel", "DC", "Star Wars", "Star Trek", "Wizarding World", "Cosmere", "Middle-earth", "Discworld", etc.
- If neither series nor universe is clearly applicable at ≥0.80 confidence, return both as null.

OUTPUT (JSON only)
{{
  "series": "Series name" | null,
  "universe": "Shared universe name" | null,
  "evidence": {{
    "series":   {{ "from": "summary|world", "note": "…" }} | null,
    "universe": {{ "from": "summary|world", "note": "…" }} | null
  }},
  "confidence": {{
    "series": 0.0-1.0 | null,
    "universe": 0.0-1.0 | null,
    "_overall": 0.0-1.0
  }}
}}
"""

def extract_series_universe(
    config_path: str,
    title: str,
    author: str,
    publication_year: int,
    summary: str,
    llm_provider: str,
    llm_model: str,
    max_tokens: int = 800
) -> Dict[str, Any]:
    prompt = PromptTemplate(
        input_variables=["title", "author", "publication_year", "summary"],
        template=SERIES_UNIVERSE_PROMPT_TEMPLATE
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
            "genre":           B.get("genre"),
            "subgenre":        B.get("subgenre"),
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
        },
        "confidence": {
            "setting_city":    (A.get("confidence") or {}).get("setting_city"),
            "setting_region":  (A.get("confidence") or {}).get("setting_region"),
            "setting_country": (A.get("confidence") or {}).get("setting_country"),
            "setting_era":     (A.get("confidence") or {}).get("setting_era"),
            "setting_time":    (A.get("confidence") or {}).get("setting_time"),
            "genre":           (B.get("confidence") or {}).get("genre"),
            "subgenre":        (B.get("confidence") or {}).get("subgenre"),
            "_overall":        None
        },
        "notes": B.get("notes") or ""
    }
    return result
