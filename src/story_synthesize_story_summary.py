# synthesize_story_summary.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import re, json

from langchain.prompts import PromptTemplate
from llm import load_config, get_llm, extract_json  # <- matches your project


import os, io, json, re
from typing import Iterable, Tuple

SUMMARY_KEY_HINTS = re.compile(r"(summary|synopsis|plot|overview|recap|abstract)$", re.I)

def _ingest_summaries(summaries_or_paths: Iterable[str], max_sources: int = 50) -> Tuple[list[str], list[dict]]:
    """
    Accepts a mix of:
      - raw summary strings
      - file paths to .txt (plain) or .json (composite)
    Returns:
      cleaned_texts: List[str]
      provenance:    List[{"source_index": i, "origin": "...", "type": "raw|txt|json", "path": "..."}]
    """
    texts: list[str] = []
    prov: list[dict] = []

    for item in summaries_or_paths:
        if isinstance(item, str) and os.path.isfile(item):
            path = item
            ext = os.path.splitext(path)[1].lower()
            if ext in (".txt", ".md"):
                with open(path, "r", encoding="utf-8") as f:
                    t = f.read()
                t = _clean_text(t)
                if t:
                    prov.append({"origin": os.path.basename(path), "type": "txt", "path": path})
                    texts.append(t)

            elif ext == ".json":
                with open(path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}
                # Extract summary-like strings from arbitrary JSON
                found = _extract_summary_strings_from_json(data)
                for s in found:
                    t = _clean_text(s)
                    if t:
                        prov.append({"origin": os.path.basename(path), "type": "json", "path": path})
                        texts.append(t)
            else:
                # unknown file type → skip quietly
                continue
        else:
            # treat as raw text
            t = _clean_text(str(item or ""))
            if t:
                prov.append({"origin": "raw", "type": "raw"})
                texts.append(t)

    # De-dup identical texts
    uniq: list[str] = []
    uniq_idx = []
    seen = set()
    for i, t in enumerate(texts):
        k = (t[:200], len(t))  # cheap key
        if k in seen:
            continue
        seen.add(k)
        uniq.append(t)
        uniq_idx.append(i)

    # If too many, keep the longest first (good heuristic for coverage)
    if len(uniq) > max_sources:
        order = sorted(range(len(uniq)), key=lambda i: len(uniq[i]), reverse=True)[:max_sources]
        uniq = [uniq[i] for i in order]
        prov = [prov[uniq_idx[i]] for i in order]
    else:
        prov = [prov[i] for i in uniq_idx]

    return uniq, prov

def _extract_summary_strings_from_json(data) -> list[str]:
    """
    Very forgiving: walks JSON and collects any strings that look like summaries.
    Rules:
      - Keys that match SUMMARY_KEY_HINTS
      - Longish strings (>= 200 chars) anywhere
      - Arrays of strings/dicts are traversed
    """
    results: list[str] = []
    def walk(node, keypath: list[str]):
        if isinstance(node, dict):
            for k, v in node.items():
                walk(v, keypath + [str(k)])
        elif isinstance(node, list):
            for v in node:
                walk(v, keypath)
        elif isinstance(node, str):
            key_str = keypath[-1] if keypath else ""
            if SUMMARY_KEY_HINTS.search(key_str) or len(node.strip()) >= 200:
                results.append(node)
    try:
        walk(data, [])
    except Exception:
        pass
    return results



@dataclass
class SynthesisResult:
    final_summary: str
    merged_outline: List[Dict[str, Any]]
    source_ratings: List[Dict[str, Any]]
    notes: Dict[str, Any]

# -------- Public entry points ------------------------------------------------

def choose_or_synthesize_summary(
    *,
    author: str,
    title: str,
    protagonist: str,
    summaries: List[str],
    # Option A: pass a prebuilt llm (recommended if you already have one in the caller)
    llm=None,
    # Option B: OR pass provider/model + config path to build locally
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None,
    config_path: Optional[str] = None,
    max_tokens: int = 2000,
    use_llm_synthesis: bool = True,
    language: str = "English",
    target_length_words: Tuple[int, int] = (350, 650),
    require_end_to_100: bool = True,
    temperature_json: float = 0.2,
    temperature_text: float = 0.4,
) -> Tuple[str, Optional[SynthesisResult]]:
    """
    Backward-compatible: if use_llm_synthesis=False, returns the longest summary.
    Otherwise runs the 2-stage synth (audit->merge->write).
    """
    if not summaries:
        raise ValueError("No summaries provided.")
    if not use_llm_synthesis:
        return max(summaries, key=lambda s: len(s or "")), None

    # Build llm if not provided
    if llm is None:
        if not (llm_provider and llm_model and config_path):
            raise ValueError("Provide either `llm` or (llm_provider, llm_model, config_path).")
        config = load_config(config_path=config_path)
        llm = get_llm(llm_provider, llm_model, config, max_tokens=max_tokens, temperature=temperature_text)

    result = synthesize_story_summary(
        author=author, title=title, protagonist=protagonist,
        summaries=summaries, llm=llm, language=language,
        target_length_words=target_length_words, require_end_to_100=require_end_to_100,
        temperature_json=temperature_json, temperature_text=temperature_text
    )
    return result.final_summary, result


def synthesize_story_summary(
    *,
    author: str,
    title: str,
    protagonist: str,
    summaries: List[str],
    llm,                                  # REQUIRED (prebuilt via get_llm or passed in)
    language: str = "English",
    target_length_words: Tuple[int, int] = (350, 650),
    require_end_to_100: bool = True,
    temperature_json: float = 0.2,
    temperature_text: float = 0.4,
) -> SynthesisResult:
    cleaned, provenance = _ingest_summaries(summaries, max_sources=50)  # cap optional

    if not cleaned:
        raise ValueError("No non-empty summaries were found. If you provided JSON, ensure it contains long text fields or keys like 'summary', 'synopsis', 'plot'.")


    # ---------- Stage A: Audit & Extract (JSON) ----------
    audit_prompt_tmpl = PromptTemplate(
        input_variables=["author", "title", "protagonist", "language", "sources_block"],
        template=_AUDIT_TEMPLATE,
    )
    audit_user = audit_prompt_tmpl | llm  # pipe style
    audit_out = audit_user.invoke({
        "author": author,
        "title": title,
        "protagonist": protagonist,
        "language": language,
        "sources_block": "\n\n".join(
            f"<source index='{i}'>\n{txt}\n</source>" for i, txt in enumerate(cleaned)
        ),
    })

    audit_text = audit_out.content if hasattr(audit_out, "content") else str(audit_out)
    audit = _safe_extract_json(audit_text)
    source_ratings = audit.get("sources", [])
    extracted_events = audit.get("events", [])

    # ---------- Stage A.2: Merge events ----------
    merged_outline = _merge_events(extracted_events)

    # ---------- Stage B: Write Final Master Summary (prose) ----------
    writer_prompt_tmpl = PromptTemplate(
        input_variables=[
            "author", "title", "protagonist", "language",
            "min_w", "max_w", "guideline", "merged_outline_json"
        ],
        template=_WRITER_TEMPLATE,
    )
    writer = writer_prompt_tmpl | llm
    final_out = writer.invoke({
        "author": author,
        "title": title,
        "protagonist": protagonist,
        "language": language,
        "min_w": target_length_words[0],
        "max_w": target_length_words[1],
        "guideline": (
            "Ensure the story progresses from beginning to end and clearly reaches the ending."
            if require_end_to_100 else
            "Cover the full story arc as well as sources allow."
        ),
        "merged_outline_json": json.dumps(merged_outline, ensure_ascii=False, indent=2),
    })
    final_summary = final_out.content if hasattr(final_out, "content") else str(final_out)
    final_summary = _tighten(final_summary)

    return SynthesisResult(
        final_summary=final_summary,
        merged_outline=merged_outline,
        source_ratings=source_ratings,
        notes={
            "n_input_summaries": len(cleaned),
            "target_length_words": target_length_words,
            "temperatures": {"json": temperature_json, "text": temperature_text},
            "provenance": provenance,  # <- add this
        },
)


# -------- Prompt templates (match your Runnable style) -----------------------

_AUDIT_TEMPLATE = """You are a meticulous story synthesis assistant working in {language}.
Your job: audit several summaries of the same story and extract a protagonist-centered,
chronological list of concrete events (actions, things that happen to the protagonist, decisions, turning points).
Avoid themes or analysis.

STORY:
<author>{author}</author>
<title>{title}</title>
<protagonist>{protagonist}</protagonist>

SOURCES (may overlap or conflict; some are weak):
{sources_block}

TASKS:
1) Rate each source on:
   - completeness_0_10
   - protagonist_focus_0_10
   - concreteness_0_10
   - chronology_0_10
   - spoilage_profile (none|partial|full)
   - notes (short)
2) Extract a unified event set through the protagonist’s eyes:
   - For each event:
     * "event": 1–2 sentences of concrete action focused on the protagonist
     * "approx_position": one of ["setup","early","rising","midpoint","late","climax","resolution"]
     * "sources": list of source indices that support this event
   - Keep plausible chronology; when conflicts exist, prefer majority + higher-rated sources.

OUTPUT:
Return STRICT JSON with keys "sources" and "events".
"""

_WRITER_TEMPLATE = """AUTHOR: {author}
TITLE: {title}
PROTAGONIST: {protagonist}
LANGUAGE: {language}

MERGED OUTLINE (chronological events from multiple sources):
{merged_outline_json}

Write a SINGLE flowing prose summary (no bullet points, no headings), {min_w}–{max_w} words.
- Focus exclusively on what the protagonist DOES, EXPERIENCES, and DECIDES.
- Use clear narrative sentences; concrete actions only (avoid themes/analysis).
- Keep the implied chronology. {guideline}

Return ONLY the summary text.
"""

# -------- Merge + utilities --------------------------------------------------

def _merge_events(extracted_events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # Accept either a flat list or [{events:[...]}] style
    if extracted_events and isinstance(extracted_events[0], dict) and "events" in extracted_events[0]:
        flat = []
        for block in extracted_events:
            flat.extend(block.get("events", []))
        events = flat
    else:
        events = extracted_events or []

    order = ["setup", "early", "rising", "midpoint", "late", "climax", "resolution"]
    buckets = {k: [] for k in order}
    for ev in events:
        pos = ev.get("approx_position", "rising")
        pos = pos if pos in buckets else "rising"
        buckets[pos].append(ev)

    def key(e: Dict[str, Any]) -> str:
        return re.sub(r"\W+", " ", (e.get("event") or "").lower()).strip()

    seen = {}
    merged = []
    for pos in order:
        for ev in buckets[pos]:
            k = key(ev)
            if not k:
                continue
            if k in seen:
                seen[k]["sources"] = sorted(set(seen[k]["sources"] + ev.get("sources", [])))
            else:
                rec = {
                    "event": (ev.get("event") or "").strip(),
                    "approx_position": pos,
                    "sources": sorted(set(ev.get("sources", []))),
                }
                seen[k] = rec
                merged.append(rec)

    merged = [m for m in merged if _is_concrete(m["event"])]
    return merged

def _clean_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^summary\s*[:\-]\s*", "", s, flags=re.I)
    return s

def _tighten(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s

def _is_concrete(text: str) -> bool:
    abstract_terms = ("theme", "symbol", "explores", "critiques", "society", "motif", "allegory")
    if any(t in (text or "").lower() for t in abstract_terms):
        return False
    return bool(re.search(
        r"\b(\w+ed|\bis\b|\bare\b|\bwas\b|\bwere\b|\bdoes\b|\bdo\b|\bdecides?\b|\bchooses?\b|\bmeets?\b|\bflees?\b|\bfights?\b)\b",
        text or "")
    )

def _safe_extract_json(raw: str) -> Dict[str, Any]:
    """
    Use your project helper first (extract_json), then fallback to regex.
    """
    try:
        j = extract_json(raw)
        if isinstance(j, dict):
            return j
    except Exception:
        pass

    # fallback: best-effort JSON block extraction
    m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return {"sources": [], "events": []}


####
## HELPERS
import os, json, re, datetime
from typing import Optional

def _safe_slug(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9\-._]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "item"

def save_synthesis_debug(
    *,
    result: "SynthesisResult",
    title: str,
    protagonist: str,
    debug_dir: str = "data/_summary_debug",
    prefix: Optional[str] = None,
    source_previews: Optional[list[str]] = None,
    provenance: Optional[list[dict]] = None,
) -> dict:
    """
    Saves:
      - master summary as TXT
      - full debug as JSON (outline + source ratings + notes)
    Returns filepaths dict for convenience.
    """
    os.makedirs(debug_dir, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base = f"{prefix+'_' if prefix else ''}{_safe_slug(title)}--{_safe_slug(protagonist)}--{ts}"

    paths = {
        "summary_txt": os.path.join(debug_dir, f"{base}.summary.txt"),
        "debug_json": os.path.join(debug_dir, f"{base}.debug.json"),
    }

    # Write master summary (.txt)
    with open(paths["summary_txt"], "w", encoding="utf-8") as f:
        f.write(result.final_summary.strip() + "\n")

    # Write full debug (.json)
    payload = {
        "final_summary_word_count": len(result.final_summary.split()),
        "final_summary": result.final_summary,
        "merged_outline": result.merged_outline,
        "source_ratings": result.source_ratings,
        "notes": result.notes,
        "meta": {
            "title": title,
            "protagonist": protagonist,
            "saved_at": ts,
        },
    }
    if source_previews is not None:
        payload["source_previews"] = [
            {"index": i, "len": len(s), "preview": s[:240]}
            for i, s in enumerate(source_previews)
        ]
    if provenance is not None:
        payload["provenance"] = provenance

    with open(paths["debug_json"], "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return paths



###

# story_summary.py (caller)
# from synthesize_story_summary import choose_or_synthesize_summary
from llm import load_config, get_llm

def get_best_summary(author, title, protagonist, candidate_summaries,
                     use_llm=True, llm_provider="openai", llm_model="gpt-4o-mini",
                     config_path="config.yaml"):

    print("starting")
    # Build the LLM using your existing approach
    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=2000)

    summary, debug = choose_or_synthesize_summary(
        author=author,
        title=title,
        protagonist=protagonist,
        summaries=candidate_summaries,
        llm=llm,                       # pass the runnable LLM
        use_llm_synthesis=use_llm,
        target_length_words=(400, 700),  # optional tweak
        require_end_to_100=True,
    )

    # Save while testing
    if debug:
        paths = save_synthesis_debug(
            result=debug,
            title=title,
            protagonist=protagonist,
            debug_dir="data/_summary_debug",  # customize if you like
            prefix="test",                    # optional prefix tag
        )
        print("Saved summary + debug:", paths)

    # if you want to save debug artifacts, do it here with `debug`
    return summary

get_best_summary(
    author="Victor Hugo",
    title="Les Misérables",
    protagonist="Jean Valjean",
    candidate_summaries="/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/les_miserables_composite_data.json",           # pass the runnable LLM
    use_llm=True, llm_provider="openai", llm_model="gpt-4o-mini",
    config_path="config.yaml")

