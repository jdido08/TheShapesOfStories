# create_description.py
from llm import load_config, get_llm, extract_json  # keep your existing helpers
from langchain.chains import LLMChain               # kept for parity with your imports
from langchain.prompts import PromptTemplate        # kept for parity with your imports
import yaml
import tiktoken
import json
import os
import base64
import mimetypes
from pathlib import Path
from typing import Optional, Union, Dict, Any, List
from langchain_core.messages import HumanMessage

# --- your existing config knobs ---
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

def _encode_image_to_data_url(image_path: Optional[str]) -> tuple[Optional[str], Optional[str]]:
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
      - Uses 'symbolic_representation' and (if not "Other") 'archetype'
        inside **The Story Behind the Shape** section.
    """
    # 1) Load config + model just like you already do
    config = load_config(config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=8192)

    # 2) Optional image
    image_mime_type, base64_image = _encode_image_to_data_url(image_path)

    # 3) Story JSON (source of truth)
    story = _load_story_data(story_json_or_path)

    title = (story or {}).get("title") or (story or {}).get("work_title") or ""
    author = (story or {}).get("author") or ""
    protagonist = (story or {}).get("protagonist") or ""
    symbolic = (story or {}).get("symbolic_representation") or ""
    archetype = (story or {}).get("archetype") or ""
    arc_texts_inline = _collect_arc_texts(story)

    # 4) Prompt (revised only for Story-Behind section requirements)
    prompt_text = f"""
You're a literary + marketing expert. Create a polished Shopify product description
for the attached "Shape of Story" artwork. Use the STORY DATA as the single source
of truth; the image is for tone only. Identify title, author, and protagonist from JSON.

Return only the final prose (no markdown headings, no labels).

1) Headline:
   The Shape of "{title}" — {protagonist}'s Journey

2) Opening hook (1–2 sentences, spoiler-light):
   • Invite the reader; state what this print celebrates about the book.

3) The Story Behind the Shape (2–4 sentences, ~45–90 words):
   • Explain the journey using arrow notation inline, e.g., "(↓)", "(↑)", "(→)".
   • Use THIS exact left-to-right symbolic string as the journey: {symbolic}
   • Describe what each movement means for {protagonist}'s fortunes (up = better, down = worse).
   • If an archetype exists and is not "Other", briefly name it and why this shape fits. Archetype: {archetype}
   • Ground claims lightly in these beat cues when helpful (keep it narrative, not a list):
     {arc_texts_inline}
   • Do not say "graph/curve/line"; instead refer to the journey and its symbols.

4) Display details (2–3 short sentences):
   • Note that the path is composed of concise story beats on a minimalist layout.
   • Mention premium/archival materials in general terms.
   • Suggest where it looks great (reading nook, office, classroom).

[STORY_JSON_START]
{json.dumps(story or {}, ensure_ascii=False)}
[STORY_JSON_END]
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


# ======== Back-compat name (your old entry point) ========
def create_product_description(
    image_path: Optional[str] = None,
    story_json_or_path: Union[str, Dict[str, Any], None] = None
) -> str:
    """Thin wrapper to preserve your original function name/signature."""
    return create_description(image_path=image_path, story_json_or_path=story_json_or_path)


image_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-pride-and-prejudice_protagonist-elizabeth-bennet_product-print_size-8x10_line-type-char_background-color-#1B365D_font-color-#F5E6D3_border-color-FFFFFF_font-Baskerville_title-display-yes.png"
story_json_or_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/pride-and-prejudice_elizabeth-bennet_8x10.json"
text = create_product_description(
    image_path=image_path,
    story_json_or_path=story_json_or_path
)
print(text)
