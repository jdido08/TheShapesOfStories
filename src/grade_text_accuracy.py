
# grade_arc_text_accuracy.py
"""
Grades the accuracy/quality of the *arc_text* phrases for each story component.
Follows the structure of `grade_shape_accuracy.py` by exposing:
  - grade_arc_text_accuracy(generated_analysis: dict) -> dict
  - assess_arc_text(generated_analysis_path: str) -> None

It writes results back into the source JSON under:
  data['quality_assessment']['text_accuracy_assessment'] = {...}
and sets/updates the 'status' accordingly.
"""

from __future__ import annotations
import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Dict, Tuple
import re

# --- Helpers -----------------------------------------------------------------

MINOR_WORDS = {
    "and","or","nor","but","so","yet",
    "a","an","the",
    "of","in","on","at","to","from","by","for","with","as","into","onto","upon","over","under","off","per","than"
}

def _normalize(s: str) -> str:
    # Lowercase, normalize apostrophes, drop possessive, remove punctuation except periods
    s = s.lower().replace("’", "'")
    s = re.sub(r"'s\b", "", s)
    s = re.sub(r"[^a-z0-9\.\s-]", " ", s)  # keep periods for phrase splitting
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _tokenize_words(s: str) -> List[str]:
    s = _normalize(s)
    return [t for t in re.split(r"\s+", s) if t and t != "."]

def _strip_period(s: str) -> str:
    return s[:-1] if s.endswith(".") else s

def _titlecase_ok(phrase: str) -> Tuple[bool, List[str]]:
    """
    Check that Title Case is followed per About-page rules:
      - Each word should start with uppercase EXCEPT minor words (unless first in phrase).
    Returns (ok, issues)
    """
    issues = []
    words = phrase.split()
    if not words:
        return False, ["Empty phrase."]
    for i, w in enumerate(words):
        base = re.sub(r"[^\w-]", "", w)  # strip punctuation for the check
        if not base:
            continue
        should_capitalize = (i == 0) or (base.lower() not in MINOR_WORDS)
        # Accept hyphenated words if each part has correct casing
        if "-" in base:
            parts = base.split("-")
            if should_capitalize:
                if not all(p[:1].isupper() and p[1:].islower() for p in parts if p):
                    issues.append(f"Hyphenation casing: '{w}'")
            else:
                # minor word hyphenated: allow lowercase
                if not all(p[:1].islower() or (p[:1].isupper() and i==0) for p in parts if p):
                    # Be lenient; skip adding issue to avoid false positives
                    pass
        else:
            if should_capitalize:
                if not (base[:1].isupper() and base[1:].islower()):
                    issues.append(f"Capitalization: '{w}'")
            else:
                # minor word: allow lowercase
                if not base.islower():
                    issues.append(f"Minor word should be lowercase: '{w}'")
    return (len(issues) == 0), issues

def _phrases_from_arc_text(arc_text: str) -> List[str]:
    """
    Split arc_text into phrases.
    All phrases except the last should end with '. ' and the last with '.'
    We'll be tolerant with single-period spacing when counting.
    """
    raw = arc_text.strip()
    # Split on ". " but keep the last that ends with "."
    if not raw.endswith("."):
        return [raw]  # formatting check will flag
    parts = raw.split(". ")
    # Ensure last ends with '.' (remove trailing '.' for phrase content checks)
    phrases = []
    for i, p in enumerate(parts):
        if i < len(parts) - 1:
            # expect no trailing '.' in part (split removed the space, not the dot);
            # but users might have "...."; be defensive
            if p.endswith("."):
                p = _strip_period(p)
            phrases.append(p)
        else:
            # last contains the final '.'
            phrases.append(_strip_period(p))
    return phrases

def _format_ok(arc_text: str) -> Tuple[bool, List[str]]:
    issues = []
    if not arc_text.strip():
        return False, ["Empty arc_text."]
    if not arc_text.endswith("."):
        issues.append("Arc text must end with a single period.")
    # Check internal ". " separators
    # Any ".  " (double space) or ".. " (double dot) should be flagged
    if ".." in arc_text and "... " not in arc_text:
        issues.append("Multiple consecutive periods detected.")
    if ".  " in arc_text:
        issues.append("Double spaces after period.")
    # Ensure if multiple phrases, separators are '. '
    internal = arc_text[:-1]  # drop final '.'
    if ". " in internal:
        # Good separator exists. Ensure no bare '.' remains inside
        bad = re.search(r"\.[^\s]", internal)
        if bad:
            issues.append("Incorrect phrase separator; use '. ' between phrases.")
    return (len(issues) == 0), issues

def _support_ratio(arc_text: str, description: str) -> float:
    """
    Measures how much of the arc_text content is grounded in the component description.
    We compute ratio of content words (>=3 chars, excluding MINOR_WORDS) whose stems
    appear in the description.
    """
    desc_tokens = set(_tokenize_words(description))
    def stem(w: str) -> str:
        # Very light stemmer: remove common suffixes
        for suf in ("ing","ed","es","s"):
            if len(w) > 4 and w.endswith(suf):
                return w[:-len(suf)]
        return w
    desc_stems = {stem(t) for t in desc_tokens}

    tokens = [t for t in _tokenize_words(arc_text) if len(t) >= 3 and t not in MINOR_WORDS]
    if not tokens:
        return 0.0
    hits = 0
    for t in tokens:
        if stem(t) in desc_stems:
            hits += 1
    return hits / max(1, len(tokens))

def _contains_protagonist(arc_text: str, protagonist: str) -> bool:
    prot = _normalize(protagonist)
    # Split to first/last and check each
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
    return jaccard < 0.7  # flag if very similar

def _char_count(s: str) -> int:
    return len(s)

# --- Grading -----------------------------------------------------------------

@dataclass
class ComponentTextAssessment:
    index: int
    end_time: float
    arc_text: str
    target_chars: int | None
    actual_chars: int
    length_ok: bool
    format_ok: bool
    capitalization_ok: bool
    no_protagonist_name: bool
    support_ratio: float
    distinct_from_previous: bool
    score: float
    grade: str
    issues: List[str]
    suggestions: List[str]

def _letter(score: float) -> str:
    if score >= 0.90: return "A"
    if score >= 0.80: return "B"
    if score >= 0.70: return "C"
    if score >= 0.60: return "D"
    return "F"


# === LLM Integration (mirrors grade_shape_accuracy.py style) ==================
try:
    from llm import load_config, get_llm, extract_json  # project-local helper
    from langchain.prompts import PromptTemplate
    _LLM_AVAILABLE = True
except Exception as _e:
    _LLM_AVAILABLE = False

def _build_llm_prompt():
    prompt_template = r"""
You are grading the **text labels** (arc_text) that annotate each component of a story's emotional arc.
The goal: judge whether the chosen words/phrases are **semantically correct, faithful, concise, and consistent** with
the component's description and the overall story context.

### Inputs
- **Story JSON**: {generated_analysis}
- **Canonical Summary** (objective reference): {canonical_summary}
- **Metadata**: Title = "{title}", Author = "{author}", Protagonist = "{protagonist}"

### What to check (per component)
1) **Faithfulness**: The phrase(s) accurately reflect the events/state in that segment; no invented facts.
2) **Perspective & Scope**: Fits the protagonist's arc POV and the time-scope of that segment.
3) **Semantic Clarity**: Clear, non-ambiguous, avoids purple prose; good verb/noun choice.
4) **Signal Strength**: Phrases match the *direction/intensity* implied by the emotional move (rise/fall/flat).
5) **Avoids Leakage**: Doesn't preview future beats or import context not established yet.
6) **Title Case & Style**: Concise, compelling label copy in Title Case; minor words lowercase (unless first).

### Holistic (top-down) checks
- **Voice Consistency**: Do labels feel like a cohesive set?
- **Tense/Style Consistency**: Parallel structure where possible.
- **Coverage**: Labels “cover” the narrative scaffolding without contradictions.

### Output JSON (ONLY). Do not include backticks.

{
  "text_accuracy": {
    "per_component": [
      {
        "index": <int>,                // component index in story_components
        "end_time": <number>,          // use modified_end_time if present
        "arc_text": "<string>",
        "semantic_assessment": {
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
        }
      }
    ],
    "holistic_assessment": {
      "grade": "A|B|C|D|F",
      "justification": "<concise explanation>",
      "global_suggestions": ["..."]
    },
    "final_grade": "A|B|C|D|F",
    "final_justification": "<why this final grade>"
  }
}
"""
    return PromptTemplate(
        input_variables=["generated_analysis", "canonical_summary", "title", "author", "protagonist"],
        template=prompt_template
    )

def _llm_text_grade(generated_analysis: dict, canonical_summary: str, llm_provider: str, llm_model: str, config_path: str):
    if not _LLM_AVAILABLE:
        return None  # will fall back to rule-based
    
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
        # return a marker so caller can still write mechanical checks
        return {"error": f"LLM parse error: {e}"}

def grade_arc_text_accuracy(generated_analysis: Dict, canonical_summary: str = "", llm_provider: str = "openai", llm_model: str = "gpt-4o-mini", config_path: str = "config.yaml") -> Dict:
    """
    Combined LLM + mechanical checks.
    If an LLM is available, we prefer its 'text_accuracy' block and merge in mechanical diagnostics
    under each component at 'mechanical_checks'. If not, we return purely mechanical results using
    the previous implementation.
    """
    # First, try LLM
    llm_result = _llm_text_grade(generated_analysis, canonical_summary, llm_provider, llm_model, config_path)
    # Next, compute mechanical checks
    mech = _mechanical_grade(generated_analysis)  # refactor of prior function body

    if isinstance(llm_result, dict) and llm_result.get("text_accuracy"):
        # Merge per-component by index
        llm_block = llm_result["text_accuracy"]
        mech_block = mech["text_accuracy"]
        mech_by_index = {c["index"]: c for c in mech_block.get("per_component", [])}
        merged_components = []
        for item in llm_block.get("per_component", []):
            idx = item.get("index")
            merged = dict(item)
            if idx in mech_by_index:
                merged["mechanical_checks"] = {
                    k: v for k, v in mech_by_index[idx].items()
                    if k not in {"index","end_time","arc_text"}
                }
            merged_components.append(merged)

        # Compose aggregate
        final_grade = llm_block.get("final_grade") or mech_block.get("aggregate", {}).get("final_grade") or "F"
        out = {
            "text_accuracy": {
                "per_component": merged_components,
                "holistic_assessment": llm_block.get("holistic_assessment", {}),
                "aggregate": mech_block.get("aggregate", {}),  # keep the numeric aggregates from mechanical checks
                "final_grade": final_grade,
                "final_justification": llm_block.get("final_justification", "LLM-based assessment.")
            }
        }
        return out
    else:
        # LLM unavailable or failed; return mechanical-only
        return mech

# --- Refactor prior deterministic grading into helper for reuse --------------
def _mechanical_grade(generated_analysis: Dict) -> Dict:
    comps = generated_analysis.get("story_components", [])
    protagonist = generated_analysis.get("protagonist", "")
    results: List[ComponentTextAssessment] = []

    prev_arc_text = ""
    for idx, comp in enumerate(comps):
        if comp.get("end_time", 0) == 0:
            continue  # skip initial 0 component
        arc_text = comp.get("arc_text", "") or ""
        description = comp.get("description", "") or ""
        target = comp.get("target_arc_text_chars_with_net") or comp.get("target_arc_text_chars")
        actual = _char_count(arc_text)

        issues = []
        suggestions = []

        # 1) Length
        length_ok = True
        if target is not None:
            length_ok = (actual == int(target))
            if not length_ok:
                issues.append(f"Length mismatch (actual {actual}, target {target}).")
                suggestions.append("Adjust phrase lengths or spacing to match the exact character count.")

        # 2) Formatting
        format_ok, fmt_issues = _format_ok(arc_text)
        if not format_ok:
            issues.extend(fmt_issues)
            suggestions.append("Ensure each phrase ends with '. ' except the last, which ends with '.'. Avoid double spaces.")

        # 3) Capitalization (Title Case rules)
        cap_ok_all = True
        phrases = _phrases_from_arc_text(arc_text)
        for p in phrases:
            ok, cap_issues = _titlecase_ok(p)
            if not ok:
                cap_ok_all = False
                issues.extend(cap_issues)
        if not cap_ok_all:
            suggestions.append("Use Title Case: capitalize all words except minor words (unless first).")

        # 4) Protagonist name
        no_prot = not _contains_protagonist(arc_text, protagonist)
        if not no_prot:
            issues.append("Protagonist name appears in arc_text (should be omitted).")
            suggestions.append("Remove the protagonist's name from phrases.")

        # 5) Support ratio (grounding to description)
        support = _support_ratio(arc_text, description)
        if support < 0.5:
            issues.append(f"Low grounding in component description (support ratio {support:.2f}).")
            suggestions.append("Use concrete words from the component description; avoid new info not present there.")

        # 6) Distinctness from previous
        distinct = _distinct_from_previous(arc_text, prev_arc_text)
        if not distinct:
            issues.append("Arc text is highly similar to previous segment.")
            suggestions.append("Revise to capture distinct beats for this segment, avoiding repetition.")

        # Weighted score
        score = (
            (1.0 if length_ok else 0.0) * 0.20 +
            (1.0 if format_ok else 0.0) * 0.10 +
            (1.0 if cap_ok_all else 0.0) * 0.10 +
            (1.0 if no_prot else 0.0) * 0.10 +
            (support) * 0.40 +
            (1.0 if distinct else 0.0) * 0.10
        )

        results.append(ComponentTextAssessment(
            index=idx,
            end_time=comp.get("modified_end_time", comp.get("end_time", 0)),
            arc_text=arc_text,
            target_chars=int(target) if target is not None else None,
            actual_chars=actual,
            length_ok=length_ok,
            format_ok=format_ok,
            capitalization_ok=cap_ok_all,
            no_protagonist_name=no_prot,
            support_ratio=round(support, 3),
            distinct_from_previous=distinct,
            score=round(score, 3),
            grade=_letter(score),
            issues=issues,
            suggestions=list(dict.fromkeys(suggestions))[:4]
        ))

        prev_arc_text = arc_text

    if results:
        avg_support = sum(r.support_ratio for r in results) / len(results)
        avg_score = sum(r.score for r in results) / len(results)
        final_grade = _letter(avg_score)
    else:
        avg_support = 0.0
        avg_score = 0.0
        final_grade = "F"

    return {
        "text_accuracy": {
            "per_component": [asdict(r) for r in results],
            "aggregate": {
                "components_graded": len(results),
                "avg_support_ratio": round(avg_support, 3),
                "avg_score": round(avg_score, 3),
                "final_grade": final_grade
            }
        }
    }


def assess_arc_text(generated_analysis_path: str, canonical_summary: str = "", config_path: str = 'config.yaml', llm_provider: str = 'openai', llm_model: str = 'gpt-4o-mini') -> None:
    """
    Loads a story JSON, grades arc_text accuracy, and writes the results back.
    Mirrors the 'assess_story_shape' function structure from grade_shape_accuracy.py.
    """
    print(f"--- Starting Arc Text Accuracy Assessment for {generated_analysis_path} ---")

    if not os.path.exists(generated_analysis_path):
        print(f"Error: File not found at {generated_analysis_path}")
        return

    with open(generated_analysis_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    try:
        text_grade_result = grade_arc_text_accuracy(data, canonical_summary=canonical_summary, llm_provider=llm_provider, llm_model=llm_model, config_path=config_path)
    except Exception as e:
        print("Error during text grading:", e)
        data.setdefault("quality_assessment", {})
        data["quality_assessment"]["text_accuracy_assessment"] = {
            "status": "grading_error",
            "error_message": str(e),
            "assessment_timestamp": datetime.now().isoformat()
        }
        with open(generated_analysis_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        return

    # Prepare and save
    qa = data.setdefault("quality_assessment", {})
    qa["text_accuracy_assessment"] = text_grade_result.get("text_accuracy", {})
    qa["assessment_timestamp"] = datetime.now().isoformat()

    # Determine pass/fail based on final grade
    final_grade = qa["text_accuracy_assessment"].get("aggregate", {}).get("final_grade")
    if final_grade in ["A", "B", "C"]:
        qa["status_text_check"] = "passed_text_check"
        print(f"Assessment PASSED. Text Grade: {final_grade}")
    else:
        qa["status_text_check"] = f"failed_text_check (Grade: {final_grade})"
        print(f"Assessment FAILED. Text Grade: {final_grade}")

    with open(generated_analysis_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    print(f"Successfully updated {generated_analysis_path} with text accuracy assessment.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Grade arc_text accuracy for a story JSON.")
    parser.add_argument("json_path", help="Path to the story JSON file.")
    parser.add_argument("--summary", default="", help="Canonical summary text (optional).")
    parser.add_argument("--config", default="config.yaml", help="Path to LLM config (optional).")
    parser.add_argument("--provider", default="openai", help="LLM provider key for project llm loader (optional).")
    parser.add_argument("--model", default="gpt-4o-mini", help="LLM model name (optional).")
    args = parser.parse_args()

    
    assess_arc_text(args.json_path, canonical_summary=args.summary, config_path=args.config, llm_provider=args.provider, llm_model=args.model)