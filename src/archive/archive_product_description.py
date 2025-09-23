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
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, Dict, Any


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

def _approx_color_name(rgb: List[float]) -> str:
    """Small heuristic for friendly color names when JSON has RGB floats 0..1."""
    if not isinstance(rgb, list) or len(rgb) != 3:
        return ""
    r, g, b = rgb
    # brightness
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
        if r > 0.45 and g < 0.25 and b < 0.25:
            return "crimson"
        return "red"
    if g >= r and g >= b:
        return "green"
    return "neutral"

def _extract_font_name(story: Dict[str, Any], image_path: Optional[str]) -> str:
    """Get a human-friendly font name from JSON or the image filename (e.g., font-Baskerville)."""
    # JSON candidates
    for key in ("font_name", "font_family", "font", "title_font"):
        v = story.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()

    # Fallback: parse from filename "font-Baskerville"
    if image_path:
        name = Path(image_path).name
        m = re.search(r'font-([A-Za-z0-9\- ]+)', name)
        if m:
            return m.group(1).replace("-", " ").strip()

    return ""


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

    Structure enforced:
      1) The Shape of "[TITLE]" — [PROTAGONIST]'s Journey
      2) The Story Behind the Shape  (with bullets for Shape and Archetype* + a paragraph)
      3) Print Details               (bulleted)
      4) Ending Hook

    Changes in this revision:
      - “Beats” line refined per your wording.
      - Colors: no hex codes; ask LLM to use friendly descriptors based on the image,
        with soft JSON/filename hints. Optionally mention font if it adds value.
      - Hard-coded lines:
          • Premium 8x10" print on archival-quality paper with 0.6" white border
          • Designed for standard framing (stunning when matted in an 11x14" frame)
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

    symbolic = story.get("symbolic_representation", "") or story.get("symbolic", "")
    archetype = (story.get("archetype") or "").strip()

    # Hints for color/type line (LLM decides final wording; keep it to one line)
    bg_rgb = story.get("background_color")
    text_rgb = story.get("font_color") or story.get("title_font_color")
    bg_hint = _approx_color_name(bg_rgb) if bg_rgb else ""
    text_hint = _approx_color_name(text_rgb) if text_rgb else ""
    font_name = _extract_font_name(story, image_path)

    # Optional beat labels to ground the prose
    arc_texts_inline = _collect_arc_texts(story)

    # 4) Prompt (updated per your notes)
    #    - No hex codes.
    #    - Friendly color descriptors (LLM sees the image + hints).
    #    - Archetype appears only in the bullet (if not "Other"), not in the paragraph.
    #    - Hard-coded first & framing lines in Print Details.
    prompt_text = f"""
You are a literary + marketing expert. Write a Shopify product description for a "Shape of Story" artwork using the STORY DATA below as the only source of truth. The image (if provided) is for visual tone.

RESPONSE RULES
- Return **valid HTML only** (no Markdown, no code-fences, no extra commentary).
- Use exactly these sections and tags in this order:
  1) <h2>The Shape of "{title}" — {protagonist}’s Journey</h2>
     <p>Write 2–3 sentences. Lead with value and be conversion-friendly without hype.
        Naturally include 2–3 relevant phrases (not spammy) such as:
        “{title} print”, “{author} wall art”, “bookish décor”, “literary gift”, “reading nook”.
        Keep it fluent—do not comma-stack keywords or repeat them.</p>

  2) <h2>The Story Behind the Shape</h2>
     <ul>
       <li><strong>Shape:</strong> {symbolic if symbolic else "(not provided)"}</li>
{"     <li><strong>Archetype:</strong> " + archetype + "</li>" if (archetype and archetype.lower() != "other") else ""}
     </ul>
     <p>Write 2–4 sentences (≈45–90 words) explaining the emotional journey. Embed arrow notation inline and
        follow the Shape **as grouped tokens** left to right: {symbolic}. Keep identical consecutive arrows **together**,
        e.g., if the Shape is "↓ ↑↑ →", reference “(↓)”, “(↑↑)”, “(→)”—never split “(↑↑)” into two “(↑)”.
        Use specific moments when they clarify the rise/fall, but keep it concise and focused on the emotional movement (not a step-by-step recap). Do **not** mention archetype in this paragraph.
        Lightly ground the flow using these beat cues when helpful (keep it narrative, not a list): {arc_texts_inline}</p>

  3) <h2>Print Details</h2>
     <ul>
       <li>Premium 11x14&quot; print on archival-quality paper with white border</li>
       <li>The story’s shape is formed from concise beats positioned at the exact points along {protagonist}’s journey</li>
       <li>Write one short line that describes background + typography in natural terms (no hex codes).
           Infer from the image; you may use these hints only if accurate: background≈{(story.get("background_hint") or "") or "(use image)"}; text≈{(story.get("font_color_hint") or "") or "(use image)"}.
           Optionally name the typeface if it adds clear value (e.g., “typography in {(_extract_font_name(story, image_path) or '').strip()}”). Keep it brief.</li>
       <li>Designed for standard framing (stunning when matted in an 11x14&quot; frame)</li>
       <li>Museum-quality inks ensure lasting vibrancy and clarity</li>
     </ul>

  4) <p>Write 1–2 sentences inviting the buyer to picture the piece in their space or as a gift.
        Naturally include 1–2 phrases like “{title} poster”, “literary gift”, “gift for readers”, or “library wall art”.
        Keep it graceful and human—no keyword stuffing.</p>
     
STYLE GUARDRAILS
- Consistent tone (confident, warm, precise), sentence case, no exclamation marks.
- No extra sections, tables, or inline CSS. Keep <ul> flat (no nested lists).
- Avoid clichés (“perfect for any…”), avoid repeated keywords.
- Do not output the JSON itself.

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

def write_product_description_to_json(
    json_path: Union[str, Path],
    html: str
) -> None:
    """
    Write the generated product description HTML back to the story JSON file.
    Saves to:
      - product_description_html
      - product_description_timestamp (ISO8601)
    No-op if the path is invalid or the file can't be read.
    """
    try:
        p = Path(json_path)  # may raise if json_path isn't str/Path
        if not p.exists():
            return  # silently skip if file doesn't exist

        data: Dict[str, Any] = json.loads(p.read_text(encoding="utf-8"))
        ts = datetime.now().isoformat()

        data["product_description_html"] = html
        data["product_description_timestamp"] = ts

        p.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
    except Exception:
        # Keep this silent to avoid breaking generation; log if you have a logger
        return

def create_product_description(
    image_path: Optional[str] = None,
    story_json_or_path: Union[str, Dict[str, Any], None] = None
) -> str:
    product_description = create_description(
        image_path=image_path,
        story_json_or_path=story_json_or_path
    )

    # Strip for cleanliness
    product_description = (product_description or "").strip()

    # Only write back when we truly have a FILE PATH (not dict/None)
    if product_description and isinstance(story_json_or_path, (str, Path)):
        write_product_description_to_json(
            json_path=story_json_or_path,
            html=product_description,
        )
    return product_description


#image_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-pride-and-prejudice_protagonist-elizabeth-bennet_product-print_size-8x10_line-type-char_background-color-#1B365D_font-color-#F5E6D3_border-color-FFFFFF_font-Baskerville_title-display-yes.png"
#story_json_or_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/pride-and-prejudice_elizabeth-bennet_8x10.json"
# image_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-the-great-gatsby_protagonist-jay-gatsby_product-print_size-8x10_line-type-char_background-color-#0A1F3B_font-color-#F9D342_border-color-FFFFFF_font-Josefin Sans_title-display-yes.png"
# story_json_or_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-great-gatsby_jay-gatsby_8x10.json"
# print("starting")
# text = create_product_description(
#     image_path=image_path,
#     story_json_or_path=story_json_or_path
# )
# print(text)
