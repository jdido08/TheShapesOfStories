# grade_arc_text_accuracy.py
"""
Grades the accuracy/quality of the *arc_text* phrases for each story component.

Design:
- LLM-first: Uses your project `llm` helper + LangChain PromptTemplate to produce:
    - per-component semantic assessments
    - a holistic assessment
    - a final LLM-led grade (A/B/C/D/F)
- Mechanical FYIs (not gating pass/fail): format_ok, capitalization_ok, no_protagonist_name,
  and distinct_from_previous. Length and support_ratio are intentionally not computed.

Pass/Fail:
- status_text_check is based on the LLM final grade only (A/B/C = pass).

Outputs:
  data['quality_assessment']['text_accuracy_assessment'] = {
      "per_component": [... with "semantic_assessment" from the LLM ...],
      "holistic_assessment": {... from LLM ...},
      "final_grade": "A|B|C|D|F",
      "final_justification": "...",
      "mechanical_summary": {"components_graded": N, "all_mechanical_ok": true/false}
  }
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Tuple
import re

# --- Minor words for Title Case checks ---------------------------------------

MINOR_WORDS = {
    "and","or","nor","but","so","yet",
    "a","an","the",
    "of","in","on","at","to","from","by","for","with","as","into","onto","upon","over","under","off","per","than"
}

# --- Normalization / utilities ----------------------------------------------

def _normalize(s: str) -> str:
    s = s.lower().replace("’", "'")
    s = re.sub(r"'s\b", "", s)
    s = re.sub(r"[^a-z0-9\.\s-]", " ", s)  # keep periods/hyphens for phrase splitting
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _tokenize_words(s: str) -> List[str]:
    s = _normalize(s)
    return [t for t in re.split(r"\s+", s) if t and t != "."]

def _strip_period(s: str) -> str:
    return s[:-1] if s.endswith(".") else s

def _phrases_from_arc_text(arc_text: str) -> List[str]:
    raw = arc_text.strip()
    if not raw.endswith("."):
        return [raw]  # formatting check will flag
    parts = raw.split(". ")
    phrases = []
    for i, p in enumerate(parts):
        if i < len(parts) - 1:
            if p.endswith("."):
                p = _strip_period(p)
            phrases.append(p)
        else:
            phrases.append(_strip_period(p))
    return phrases

def _format_ok(arc_text: str) -> Tuple[bool, List[str]]:
    issues = []
    if not arc_text.strip():
        return False, ["Empty arc_text."]
    if not arc_text.endswith("."):
        issues.append("Arc text must end with a single period.")
    if ".." in arc_text and "... " not in arc_text:
        issues.append("Multiple consecutive periods detected.")
    if ".  " in arc_text:
        issues.append("Double spaces after period.")
    internal = arc_text[:-1]  # drop final '.'
    if ". " in internal:
        bad = re.search(r"\.[^\s]", internal)
        if bad:
            issues.append("Incorrect phrase separator; use '. ' between phrases.")
    return (len(issues) == 0), issues

def _titlecase_ok(phrase: str) -> Tuple[bool, List[str]]:
    issues = []
    words = phrase.split()
    if not words:
        return False, ["Empty phrase."]
    for i, w in enumerate(words):
        base = re.sub(r"[^\w-]", "", w)
        if not base:
            continue
        should_capitalize = (i == 0) or (base.lower() not in MINOR_WORDS)
        if "-" in base:
            parts = base.split("-")
            if should_capitalize:
                if not all(p[:1].isupper() and p[1:].islower() for p in parts if p):
                    issues.append(f"Hyphenation casing: '{w}'")
            else:
                # allow lowercase hyphenated minor words mid-phrase
                pass
        else:
            if should_capitalize:
                if not (base[:1].isupper() and base[1:].islower()):
                    issues.append(f"Capitalization: '{w}'")
            else:
                if not base.islower():
                    issues.append(f"Minor word should be lowercase: '{w}'")
    return (len(issues) == 0), issues

def _contains_protagonist(arc_text: str, protagonist: str) -> bool:
    prot = _normalize(protagonist)
    names = [x for x in re.split(r"\s+", prot) if x]
    text_norm = _normalize(arc_text)
    for n in names:
        if n in text_norm.split():
            return True
    return False

def _distinct_from_previous(curr: str, prev: str) -> bool:
    if not prev:
        return True
    a = set(t for t in _tokenize_words(curr) if len(t) >= 3)
    b = set(t for t in _tokenize_words(prev) if len(t) >= 3)
    if not a:
        return True
    jaccard = len(a & b) / len(a | b)
    return jaccard < 0.7

# --- Mechanical result model (FYI only) --------------------------------------

@dataclass
class MechanicalCheck:
    index: int
    end_time: float
    arc_text: str
    format_ok: bool
    capitalization_ok: bool
    no_protagonist_name: bool
    distinct_from_previous: bool
    issues: List[str]
    suggestions: List[str]
    mechanical_pass: bool

# --- LLM Integration (mirrors your grade_shape_accuracy pattern) --------------

try:
    from llm import load_config, get_llm, extract_json  # project-local helper
    # from langchain.prompts import PromptTemplate
    from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    _LLM_AVAILABLE = True
except Exception:
    _LLM_AVAILABLE = False

def _build_llm_prompt():
    # IMPORTANT: Double braces in the JSON example so LangChain doesn't treat them as variables.
    prompt_template = r"""
You are grading the **text labels** (arc_text) that annotate each component of a story's emotional arc.
The goal: judge whether the chosen words/phrases are **semantically correct, faithful, concise, and consistent** with
the component's description and the overall story context.

### Inputs
- **Story JSON**: {generated_analysis}
- **Canonical Summary** (objective reference): {canonical_summary}
- **Metadata**: Title = "{title}", Author = "{author}", Protagonist = "{protagonist}"

### What to check (per component)
1) **Faithfulness**: Accurately reflects events/state in that segment; no invented facts.
2) **Perspective & Scope**: Fits the protagonist's POV and the segment's time scope.
3) **Semantic Clarity**: Clear, non-ambiguous; strong verb/noun choice.
4) **Signal Strength**: Matches the *direction/intensity* of the emotional move.
5) **Avoids Leakage**: No spoilers from future beats.
6) **Title Case & Style**: Concise, compelling label copy in Title Case.

### Holistic (top-down) checks
- **Voice/Style Consistency**, **Coverage**, **Contradictions**.

### Output JSON (ONLY). Do not include backticks.

{{
  "text_accuracy": {{
    "per_component": [
      {{
        "index": <int>,
        "end_time": <number>,
        "arc_text": "<string>",
        "semantic_assessment": {{
          "is_faithful": true|false,
          "is_clear": true|false,
          "respects_scope": true|false,
          "matches_emotional_move": true|false,
          "avoids_future_leakage": true|false,
          "title_case_ok": true|false,
          "issues": ["..."],
          "suggestions": ["..."],
          "score": <0.0-1.0>,
          "grade": "A|B|C|D|F"
        }}
      }}
    ],
    "holistic_assessment": {{
      "grade": "A|B|C|D|F",
      "justification": "<concise explanation>",
      "global_suggestions": ["..."]
    }},
    "final_grade": "A|B|C|D|F",
    "final_justification": "<why this final grade>"
  }}
}}
"""
    return PromptTemplate(
        input_variables=["generated_analysis", "canonical_summary", "title", "author", "protagonist"],
        template=prompt_template
    )

def _llm_text_grade(generated_analysis: dict, canonical_summary: str, llm_provider: str, llm_model: str, config_path: str):
    if not _LLM_AVAILABLE:
        return None
    title = generated_analysis.get("title", "")
    author = generated_analysis.get("author", "")
    protagonist = generated_analysis.get("protagonist", "")
    prompt = _build_llm_prompt()
    gen_str = json.dumps(generated_analysis, ensure_ascii=False)
    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=3500)
    runnable = prompt | llm
    output = runnable.invoke({
        "generated_analysis": gen_str,
        "canonical_summary": canonical_summary or "",
        "title": title,
        "author": author,
        "protagonist": protagonist
    })
    output_text = output.content if hasattr(output, "content") else output
    try:
        extracted = extract_json(output_text)
        llm_dict = json.loads(extracted)
        return llm_dict
    except Exception as e:
        return {"error": f"LLM parse error: {e}"}

# --- Mechanical checks builder (FYI only; no grading) ------------------------

def _mechanical_checks(generated_analysis: Dict) -> List[MechanicalCheck]:
    comps = generated_analysis.get("story_components", [])
    protagonist = generated_analysis.get("protagonist", "")
    results: List[MechanicalCheck] = []

    prev_arc_text = ""
    for idx, comp in enumerate(comps):
        if comp.get("end_time", 0) == 0:
            continue
        arc_text = comp.get("arc_text", "") or ""
        issues, suggestions = [], []

        # 1) Formatting
        format_ok, fmt_issues = _format_ok(arc_text)
        if not format_ok:
            issues.extend(fmt_issues)
            suggestions.append("Ensure each phrase ends with '. ' except the last, which ends with '.'; avoid double spaces/periods.")

        # 2) Title Case
        cap_ok_all = True
        for p in _phrases_from_arc_text(arc_text):
            ok, cap_issues = _titlecase_ok(p)
            if not ok:
                cap_ok_all = False
                issues.extend(cap_issues)
        if not cap_ok_all:
            suggestions.append("Use Title Case: capitalize all words except minor words (unless first).")

        # 3) No protagonist name
        no_prot = not _contains_protagonist(arc_text, protagonist)
        if not no_prot:
            issues.append("Protagonist name appears in arc_text (should be omitted).")
            suggestions.append("Remove the protagonist's name from phrases.")

        # 4) Distinct from previous
        distinct = _distinct_from_previous(arc_text, prev_arc_text)
        if not distinct:
            issues.append("Arc text is highly similar to previous segment.")
            suggestions.append("Differentiate phrasing to capture distinct beats for this segment.")

        mech_pass = format_ok and cap_ok_all and no_prot and distinct
        results.append(MechanicalCheck(
            index=idx,
            end_time=comp.get("modified_end_time", comp.get("end_time", 0)),
            arc_text=arc_text,
            format_ok=format_ok,
            capitalization_ok=cap_ok_all,
            no_protagonist_name=no_prot,
            distinct_from_previous=distinct,
            issues=issues,
            suggestions=list(dict.fromkeys(suggestions)),
            mechanical_pass=mech_pass
        ))
        prev_arc_text = arc_text
    return results

# --- Public: main grading API ------------------------------------------------

def grade_arc_text_accuracy(generated_analysis: Dict, canonical_summary: str = "", llm_provider: str = "openai", llm_model: str = "gpt-4o-mini", config_path: str = "config.yaml") -> Dict:
    """
    Returns LLM-led results and attaches mechanical FYIs under each component.
    Mechanical checks do NOT affect pass/fail; they are recorded for visibility only.
    """
    llm_result = _llm_text_grade(generated_analysis, canonical_summary, llm_provider, llm_model, config_path)
    mechanical = _mechanical_checks(generated_analysis)

    out: Dict = {"text_accuracy": {"per_component": [], "holistic_assessment": {}, "final_grade": None, "final_justification": ""}}

    # 1) Merge LLM per-component with mechanical FYIs (by index)
    mech_by_idx = {m.index: m for m in mechanical}
    if isinstance(llm_result, dict) and llm_result.get("text_accuracy"):
        llm_block = llm_result["text_accuracy"]
        merged_components = []
        for item in llm_block.get("per_component", []):
            idx = item.get("index")
            merged = dict(item)
            if idx in mech_by_idx:
                merged["mechanical_checks"] = asdict(mech_by_idx[idx])
            merged_components.append(merged)
        out["text_accuracy"]["per_component"] = merged_components
        out["text_accuracy"]["holistic_assessment"] = llm_block.get("holistic_assessment", {})
        out["text_accuracy"]["final_grade"] = llm_block.get("final_grade")
        out["text_accuracy"]["final_justification"] = llm_block.get("final_justification", "LLM-based assessment.")
    else:
        # LLM missing; still return mechanical info
        out["text_accuracy"]["per_component"] = [
            {"index": m.index, "end_time": m.end_time, "arc_text": m.arc_text, "mechanical_checks": asdict(m)}
            for m in mechanical
        ]
        out["text_accuracy"]["final_grade"] = "F"
        out["text_accuracy"]["final_justification"] = "LLM unavailable or parse error."

        print("❌ ERROR: LLM failed to Grade Arc Text Accuracy")
        raise ValueError("ERROR: LLM failed to Grade Arc Text Accuracy")

    # 2) Mechanical summary (FYI only)
    mech_all_pass = all(m.mechanical_pass for m in mechanical) if mechanical else True
    out["text_accuracy"]["mechanical_summary"] = {
        "components_graded": len(mechanical),
        "all_mechanical_ok": mech_all_pass
    }
    return out

# --- Runner that updates the source JSON -------------------------------------

def assess_arc_text(generated_analysis_path: str, canonical_summary: str = "", config_path: str = 'config.yaml', llm_provider: str = 'openai', llm_model: str = 'gpt-4o-mini') -> None:
    #print(f"--- Starting Arc Text Accuracy Assessment for {generated_analysis_path} ---")

    if not os.path.exists(generated_analysis_path):
        print(f"Error: File not found at {generated_analysis_path}")
        return

    with open(generated_analysis_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not canonical_summary:
        canonical_summary = data.get('summary', '')

    try:
        text_grade_result = grade_arc_text_accuracy(
            data,
            canonical_summary=canonical_summary,
            llm_provider=llm_provider,
            llm_model=llm_model,
            config_path=config_path
        )
    except Exception as e:
        print("Error during text grading:", e)
        qa = data.setdefault("text_quality_assessment", {})
        qa["text_accuracy_assessment"] = {
            "status": "grading_error",
            "error_message": str(e),
            "assessment_timestamp": datetime.now().isoformat()
        }
        with open(generated_analysis_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return

    qa = data.setdefault("text_quality_assessment", {})
    qa["text_accuracy_assessment"] = text_grade_result.get("text_accuracy", {})
    qa["assessment_timestamp"] = datetime.now().isoformat()
    qa["grading_model"] = llm_model

    # Pass/fail is LLM-only
    final_grade = qa["text_accuracy_assessment"].get("final_grade")
    if final_grade in ["A", "B", "C"]:
        qa["status_text_check"] = "passed_text_check"
        #print(f"Assessment PASSED. Text Grade: {final_grade}")
    else:
        qa["status_text_check"] = f"failed_text_check (Grade: {final_grade})"
        #print(f"Assessment FAILED. Text Grade: {final_grade}")

    with open(generated_analysis_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    #print(f"Successfully updated {generated_analysis_path} with text accuracy assessment.")


# --- Simple "set vars and run" mode ------------------------------------------
# (Leave JSON_PATH empty to disable direct run.)
# JSON_PATH = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/for-whom-the-bell-tolls_robert-jordan_8x10.json"
# CANONICAL_SUMMARY = ""  # optional but recommended
# CONFIG_PATH = "config.yaml"
# LLM_PROVIDER = "anthropic"
# LLM_MODEL = "claude-sonnet-4-20250514"

# if JSON_PATH:
#     assess_arc_text(
#         generated_analysis_path=JSON_PATH,
#         canonical_summary=CANONICAL_SUMMARY,
#         config_path=CONFIG_PATH,
#         llm_provider=LLM_PROVIDER,
#         llm_model=LLM_MODEL,
#     )
