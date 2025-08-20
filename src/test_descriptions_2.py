# create_description.py
from llm import load_config, get_llm, extract_json  # keep your existing helpers
from langchain.chains import LLMChain               # parity with your imports
from langchain.prompts import PromptTemplate        # parity with your imports
from langchain_core.messages import HumanMessage

import json
import os
import base64
import mimetypes
from pathlib import Path
from typing import Optional, Union, Dict, Any, List, Tuple
import re

# --- your existing config knobs (unchanged) ---
config_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml'
llm_provider = 'google'
llm_model = 'gemini-2.5-pro'


# ========= helpers (minimal, additive) =========

def _load_story_data(story_json_or_path: Union[str, Dict[str, Any], None]) -> Optional[Dict[str, Any]]:
    """Accept a dict or a path to JSON and return a dict (or None)."""
    if story_json_or_path is None:
        return None
    if isinstance(story_json_or_path, dict):
        return story_json_or_path
    p = Path(str(story_json_or_path))
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def _encode_image_to_data_url(image_path: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """Return (mime_type, base64_data) or (None, None) if no image."""
    if not image_path:
        return None, None
    mime_type, _ = mimetypes.guess_type(image_path)
    if not mime_type:
        mime_type = "image/png"
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return mime_type, b64

def _collect_arc_texts(story: Optional[Dict[str, Any]]) -> str:
    """Join short beat labels to lightly ground the prose."""
    if not story:
        return ""
    comps = story.get("story_components", []) or []
    arc_texts: List[str] = []
    for c in comps:
        if isinstance(c, dict):
            val = c.get("arc_text") or c.get("label") or c.get("description")
            if isinstance(val, str) and val.strip():
                arc_texts.append(val.strip())
    return " | ".join(arc_texts)

def _rgb_to_hex(rgb: List[float]) -> str:
    """Convert [r,g,b] floats (0..1) to '#RRGGBB'."""
    r = max(0, min(255, int(round(rgb[0] * 255))))
    g = max(0, min(255, int(round(rgb[1] * 255))))
    b = max(0, min(255, int(round(rgb[2] * 255))))
    return f"#{r:02X}{g:02X}{b:02X}"

def _approx_color_name(rgb: List[float]) -> str:
    """Very small heuristic for friendly color names."""
    r, g, b = rgb
    # brightness & chroma
    brightness = (max(r, g, b) + min(r, g, b)) / 2
    if brightness > 0.93:
        return "white"
    if brightness > 0.85 and r > g >= b:
        return "soft ivory"
    # dominant channel
    if b >= r and b >= g:
        if b > 0.45 and r < 0.25 and g < 0.35:
            return "deep navy"
        return "blue"
    if r >= g and r >= b:
        return "red"
    if g >= r and g >= b:
        return "green"
    return "neutral"

def _parse_print_size_from_paths(story_json_or_path: Union[str, Dict[str, Any], None],
                                 image_path: Optional[str]) -> str:
    """Try to extract e.g. '8x10' from either filename. Fallback to '8x10'."""
    candidates = []
    if isinstance(story_json_or_path, str):
        candidates.append(Path(story_json_or_path).name)
    if image_path:
        candidates.append(Path(image_path).name)
    for name in candidates:
        m = re.search(r'(\d{1,2})x(\d{1,2})', name)
        if m:
            return f"{m.group(1)}x{m.group(2)}"
    return "8x10"

def _frame_note_for_size(size_str: str) -> str:
    """Return a friendly parenthetical for common mat/frame pairings."""
    # Specific callout requested for 8x10 -> 11x14
    if size_str == "8x10":
        return '(stunning when matted in an 11x14" frame)'
    # Generic fallback
    return "(designed for standard off-the-shelf frames)"

def _safe_num(v: Any, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return default


# ========= main function (kept structure, only revised) =========

def create_description(
    image_path: Optional[str] = None,
    story_json_or_path: Union[str, Dict[str, Any], None] = None
) -> str:
    """
    Generate a Shopify-ready product description for a Shape of Story artwork.

    Preserves your LLM structure:
      - config = load_config(...)
      - llm = get_llm(provider, model, config, max_tokens=...)
      - message = HumanMessage([...])
      - response = llm.invoke([message])

    New behavior:
      - Accepts story JSON (dict or path).
      - Outputs FOUR sections with headings:
          1) The Shape of "[TITLE]" — [PROTAGONIST]'s Journey
          2) The Story Behind the Shape  (with bullets for Shape and Archetype* + a paragraph)
          3) Print Details               (bulleted; includes “story-beats path” note)
          4) Ending Hook
      - Uses 'symbolic_representation' and (if not "Other") 'archetype'
        inside **The Story Behind the Shape** bullets, but NOT in the paragraph.
    """
    # 1) Load config + model (unchanged)
    config = load_config(config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=8192)

    # 2) Optional image
    image_mime_type, base64_image = _encode_image_to_data_url(image_path)

    # 3) Story JSON (source of truth)
    story = _load_story_data(story_json_or_path) or {}

    title = story.get("title") or story.get("work_title") or ""
    author = story.get("author") or ""
    protagonist = story.get("protagonist") or ""

    # Prefer explicit JSON fields; if symbolics missing, let the LLM still write the paragraph using beat cues
    symbolic = story.get("symbolic_representation", "") or story.get("symbolic", "")
    archetype = (story.get("archetype") or "").strip()

    # Visual + size details for Print Details section
    print_size = _parse_print_size_from_paths(story_json_or_path, image_path)  # e.g., '8x10'
    margin_in = _safe_num(story.get("fixed_margin_in_inches", 0.5), 0.5)
    margin_str = f'{margin_in:.1f}"'

    bg_rgb = story.get("background_color")
    text_rgb = story.get("font_color") or story.get("title_font_color")
    bg_hex = _rgb_to_hex(bg_rgb) if isinstance(bg_rgb, list) and len(bg_rgb) == 3 else ""
    text_hex = _rgb_to_hex(text_rgb) if isinstance(text_rgb, list) and len(text_rgb) == 3 else ""
    bg_name = _approx_color_name(bg_rgb) if isinstance(bg_rgb, list) and len(bg_rgb) == 3 else "neutral"
    text_name = _approx_color_name(text_rgb) if isinstance(text_rgb, list) and len(text_rgb) == 3 else "light"

    frame_note = _frame_note_for_size(print_size)

    # Optional beat labels to ground the prose
    arc_texts_inline = _collect_arc_texts(story)

    # 4) Prompt (updated to produce the four required sections EXACTLY)
    #    We pin the bullets’ values so the model uses them verbatim.
    #    Also: do NOT mention archetype in the explanatory paragraph.
    prompt_text = f"""
You are a literary + marketing expert. Create a polished Shopify product description
for a "Shape of Story" artwork using the STORY DATA below as the single source of truth.
The image (if provided) is for vibe/visual reference only.

OUTPUT FORMAT — return text with these four sections in this exact order:

The Shape of "{title}" — {protagonist}'s Journey
[Write 1–2 engaging sentences, spoiler-light, celebrating what this print captures about the book.]

The Story Behind the Shape
- Shape: {symbolic if symbolic else "(not provided)"}
{('- Archetype: ' + archetype) if (archetype and archetype.lower() != 'other') else ''}
[Now write 2–4 sentences (~45–90 words) explaining the journey using arrow notation inline, e.g., "(↓)", "(↑)", "(→)".]
[Describe what each movement means for {protagonist}'s fortunes (up = better, down = worse).]
[Do NOT mention the archetype in this paragraph.]
[Lightly ground the explanation using these beat cues when helpful (keep it narrative, not a list): {arc_texts_inline}]

Print Details
- Premium {print_size}" print on archival-quality paper with {margin_str} white border
- The path is composed of concise story beats that invite closer inspection on a clean, minimalist layout
- {bg_name.capitalize()} ({bg_hex}) background with {text_name} ({text_hex}) typography
- Designed for standard framing {frame_note}
- Museum-quality inks ensure lasting vibrancy and clarity

Ending Hook
[Close with 1–2 sentences that invite the buyer to imagine where it will hang or who it’s perfect for.]

STORY DATA (JSON):
{json.dumps(story, ensure_ascii=False)}
""".strip()

    # 5) Build the **same** HumanMessage you were already using
    human_content = [{"type": "text", "text": prompt_text}]
    if image_mime_type and base64_image:
        human_content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{image_mime_type};base64,{base64_image}"}
        })

    message = HumanMessage(content=human_content)

    # 6) Invoke the model exactly like you already do
    response = llm.invoke([message])
    product_description = response.content if hasattr(response, "content") else str(response)

    return product_description


# ======== Back-compat alias (if your caller still uses the old name) ========
def create_product_description(
    image_path: Optional[str] = None,
    story_json_or_path: Union[str, Dict[str, Any], None] = None
) -> str:
    return create_description(image_path=image_path, story_json_or_path=story_json_or_path)


image_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-pride-and-prejudice_protagonist-elizabeth-bennet_product-print_size-8x10_line-type-char_background-color-#1B365D_font-color-#F5E6D3_border-color-FFFFFF_font-Baskerville_title-display-yes.png"
story_json_or_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/pride-and-prejudice_elizabeth-bennet_8x10.json"
text = create_product_description(
    image_path=image_path,
    story_json_or_path=story_json_or_path
)
print(text)
