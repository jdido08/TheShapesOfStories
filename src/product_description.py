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


### INPUTS:
# Title
# Author 
# Protagonist 
# Size
# Image 
# Font Style
# Background Color Name
# Font Color Name
# Symbolic_representation
# Archetype

#Logic: 



# # --- your existing config knobs (unchanged) ---
# config_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml'
# llm_provider = 'google'
# llm_model = 'gemini-2.5-pro'

matt_frame_size = {
    "8x10": "11x14",
    "11x14": "16x20"
}


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



import html
from bs4 import BeautifulSoup

_ALLOWED_TAGS = {"h2","p","ul","li","strong","em","br","code"}
_ALLOWED_ATTRS = set()

def _shopify_sanitize(html_in: str) -> str:
    try:
        soup = BeautifulSoup(html_in, "html.parser")
        for t in soup(["script","style","link","meta","title","head","html","body"]):
            t.decompose()
        for tag in soup.find_all(True):
            if tag.name not in _ALLOWED_TAGS:
                tag.unwrap()
            else:
                for attr in list(tag.attrs):
                    if attr not in _ALLOWED_ATTRS:
                        del tag.attrs[attr]
        return str(soup).strip()
    except Exception:
        return html_in


import re

_YOOSOUND_PREFIXES = (
    "uni", "univ", "urol", "euro", "ewe", "euc", "uter", "use", "user", "ukulele"
)
_SILENT_H_PREFIXES = ("honest", "honor", "heir", "hour")

def _indef_article(phrase: str) -> str:
    """
    Choose 'a' or 'an' for the start of `phrase` based on common English pronunciation rules.
    Designed for short descriptors like color names ('ivory', 'navy', 'emerald green').
    """
    if not phrase:
        return "a"

    w = phrase.strip().lower()

    # If phrase starts with a number or an acronym (letters separated by non-letters),
    # decide based on the spoken first symbol.
    # Letters that start with vowel sounds when spelled out: A, E, F, H, I, L, M, N, O, R, S, X
    if re.match(r"^[0-9]", w):
        # Numbers starting with vowel sound: 8, 11, 18, etc. (anything starting with 8 or 11-like)
        return "an" if w.startswith(("8", "11", "18")) else "a"
    if re.match(r"^[^a-z]*[a-z]($|[^a-z])", w):
        first_letter = re.sub(r"[^a-z]", "", w)[:1]
        if len(first_letter) == 1 and first_letter in set("aefhilmnorsx"):
            # 'F' → 'eff', 'H' → 'aitch', 'R' → 'ar', etc.
            return "an"

    # Silent 'h' cases
    for pref in _SILENT_H_PREFIXES:
        if w.startswith(pref):
            return "an"

    # 'You' sound at start (e.g., 'unique', 'university', 'European')
    for pref in _YOOSOUND_PREFIXES:
        if w.startswith(pref):
            return "a"

    # Default vowel vs consonant rule on first letter
    return "an" if w[0] in "aeiou" else "a"


# ========= main function (kept structure, only revised) =========

def create_description(
    image_path: Optional[str] = None,
    story_json_or_path: Union[str, Dict[str, Any], None] = None,
    config_path: Optional[str] = None,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None 
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
    year = story.get("year") or ""
    symbolic = story.get("shape_symbolic_representation", "") or story.get("symbolic", "")
    archetype = (story.get("shape_archetype") or "").strip()
    size = story.get("product_size") or ""
    background_color_name = story.get("background_color_name") or ""
    font_color_name = story.get("font_color_name") or ""
    font_style = story.get("font_style") or ""

    article = _indef_article(background_color_name)


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
    <ul>
       <li><strong>Title:</strong> {title} <em>({year})</em></li>
       <li><strong>Author:</strong> {author}</li>
       <li><strong>Protagonist:</strong> {protagonist}</li>
       <li><strong>Shape:</strong> {symbolic}{" <em>(" + archetype + ")</em>" if (archetype and archetype.strip().lower() not in {'other','n/a','na','none'}) else ""}</li>
     </ul>
        
  2) <h2>The Story Behind the Shape</h2>
     <p>Write 2–4 sentences (≈45–90 words) explaining the emotional journey. Embed arrow notation inline and
        follow the Shape **as grouped tokens** left to right: {symbolic}. Keep identical consecutive arrows **together**,
        e.g., if the Shape is "↓ ↑↑ →", reference “(↓)”, “(↑↑)”, “(→)”—never split “(↑↑)” into two “(↑)”.
        Use specific moments when they clarify the rise/fall, but keep it concise and focused on the emotional movement (not a step-by-step recap). Do **not** mention archetype in this paragraph.
        Lightly ground the flow using these beat cues when helpful (keep it narrative, not a list): {arc_texts_inline}</p>

  3) <h2>Print Details</h2>
     <ul>
       <li>Premium {size}&quot; print on archival-quality paper with white border</li>
       <li>The shape maps key moments in {protagonist}’s journey.</li>
       <li>Features {font_style} typography in {font_color_name} on {article} {background_color_name} background</li>
       <li>Fits into standard {size}&quot; frame (or a {matt_frame_size[size]}&quot; frame matted to {size}&quot;)</li>
       <li>Ships unframed (print only)</li>
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

    #clean production description
    product_description = _shopify_sanitize(product_description)

    return product_description

def write_product_description_to_json(
    json_path: Union[str, Path],
    full_description: str,
    title_block: str,
    story_behind: str,
    print_details: str,
    ending_hook: str
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

        data["product_description_html"] = full_description,
        data["product_description_title_block_html"] = title_block,
        data["product_description_story_behind_html"] = story_behind,
        data["product_description_print_details_html"] = print_details,
        data["product_description_ending_hook_html"] = ending_hook,
        data["product_description_timestamp"] = ts

        p.write_text(json.dumps(data, ensure_ascii=False, indent=4), encoding="utf-8")
    except Exception:
        # Keep this silent to avoid breaking generation; log if you have a logger
        return

def create_product_description(
    image_path: Optional[str] = None,
    story_json_or_path: Union[str, Dict[str, Any], None] = None,
    config_path: Optional[str] = None,
    llm_provider: Optional[str] = None,
    llm_model: Optional[str] = None 
) -> str:
    product_description = create_description(
        image_path=image_path,
        story_json_or_path=story_json_or_path,
        config_path=config_path,
        llm_provider=llm_provider,
        llm_model=llm_model
    )

    # Strip for cleanliness
    product_description = (product_description or "").strip()

    #extract parts of product description 
    parsed_description = parse_description_sections(product_description)
    product_description_title_block = parsed_description["title_block"]["html"]      # HTML fragment
    product_description_story_behind = parsed_description["story_behind"]["html"]      # HTML fragment
    product_description_print_details = parsed_description["print_details"]["html"]     # HTML fragment
    product_description_ending_hook = parsed_description["ending_hook"]["html"]     # HTML fragment


    # Only write back when we truly have a FILE PATH (not dict/None)
    if product_description and isinstance(story_json_or_path, (str, Path)):
        write_product_description_to_json(
            json_path=story_json_or_path,
            full_description=product_description,
            title_block=product_description_title_block,
            story_behind=product_description_story_behind,
            print_details=product_description_print_details,
            ending_hook=product_description_ending_hook
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

#### 10/17/2025 #### EXTRACT DESCRIPTION COMPONENTS

from bs4 import BeautifulSoup
from typing import Dict, List, Optional, Iterable, Tuple

# Map canonical keys → matchers used to find the section heading(s).
SECTION_MATCHERS = {
    "title_block": ["the shape of", "—", " - ", "–"],  # tolerant to dash styles / separators
    "story_behind": ["the story behind the shape"],
    "print_details": ["print details"],
    "ending_hook": ["ending hook"],  # optional; many descriptions just end with a paragraph (no <h2>)
}

HEADING_TAGS = {"h1", "h2", "h3"}

def _collect_until_next_heading(start_tag) -> List:
    """Collect element siblings after start_tag until the next heading (h1/h2/h3) or end."""
    items = []
    for sib in start_tag.next_siblings:
        if getattr(sib, "name", None) in HEADING_TAGS:
            break
        if getattr(sib, "name", None):  # only keep element nodes
            items.append(sib)
    return items

def _first_heading(soup, predicates: List[str]):
    """Find the first h1/h2/h3 whose normalized text contains ALL tokens in predicates (case-insensitive)."""
    preds = [t.lower() for t in predicates]
    for h in soup.find_all(list(HEADING_TAGS)):
        text = h.get_text(" ", strip=True).lower()
        if all(p in text for p in preds):
            return h
    return None

def _html_and_text(nodes: List) -> Tuple[str, str]:
    frag_html = "".join(str(n) for n in nodes)
    # Make a tiny soup to get text
    frag_soup = BeautifulSoup(frag_html, "html.parser")
    frag_text = frag_soup.get_text("\n", strip=True)
    return frag_html, frag_text

def parse_description_sections(
    html: str,
    include_heading: bool = True,
) -> Dict[str, Dict[str, str]]:
    """
    Parse the full HTML product description into four canonical sections:
    - title_block
    - story_behind
    - print_details
    - ending_hook  (if present; else may be empty)

    Returns: { section_key: { "html": ..., "text": ... }, ... }
    """
    soup = BeautifulSoup(html, "html.parser")

    out = {k: {"html": "", "text": ""} for k in SECTION_MATCHERS.keys()}

    # 1) Title block: assume the FIRST <h2> (or h1/h3) is the title block heading,
    #    even if its text doesn’t literally match "the shape of", to be robust.
    #    But if a heading matching SECTION_MATCHERS["title_block"] exists, prefer that.
    title_h = _first_heading(soup, SECTION_MATCHERS["title_block"]) or \
              soup.find(list(HEADING_TAGS))
    if title_h:
        nodes = [title_h] + _collect_until_next_heading(title_h)
        if not include_heading:
            nodes = nodes[1:]
        out["title_block"]["html"], out["title_block"]["text"] = _html_and_text(nodes)

    # 2) Story Behind the Shape
    story_h = _first_heading(soup, SECTION_MATCHERS["story_behind"])
    if story_h:
        nodes = [story_h] + _collect_until_next_heading(story_h)
        if not include_heading:
            nodes = nodes[1:]
        out["story_behind"]["html"], out["story_behind"]["text"] = _html_and_text(nodes)

    # 3) Print Details
    details_h = _first_heading(soup, SECTION_MATCHERS["print_details"])
    if details_h:
        nodes = [details_h] + _collect_until_next_heading(details_h)
        if not include_heading:
            nodes = nodes[1:]
        out["print_details"]["html"], out["print_details"]["text"] = _html_and_text(nodes)

        # Bonus: bullets array for convenience
        ul = BeautifulSoup(out["print_details"]["html"], "html.parser").select("ul > li")
        out["print_details"]["bullets"] = [li.get_text(" ", strip=True) for li in ul]

    # 4) Ending hook (revised): start AFTER the first <ul> following "Print Details"
    hook_h = _first_heading(soup, SECTION_MATCHERS["ending_hook"])
    if hook_h:
        nodes = [hook_h] + _collect_until_next_heading(hook_h)
        if not include_heading:
            nodes = nodes[1:]
        out["ending_hook"]["html"], out["ending_hook"]["text"] = _html_and_text(nodes)
    else:
        if details_h:
            # Find the first <ul> after the Print Details heading
            first_ul_after_details = None
            for sib in details_h.next_siblings:
                if getattr(sib, "name", None) in HEADING_TAGS:
                    break  # no ending hook content if another section starts
                if getattr(sib, "name", None) == "ul":
                    first_ul_after_details = sib
                    break

            # Collect nodes AFTER that UL (e.g., the final <p>)
            tail_nodes = []
            if first_ul_after_details:
                for sib in first_ul_after_details.next_siblings:
                    if getattr(sib, "name", None) in HEADING_TAGS:
                        break
                    if getattr(sib, "name", None):
                        tail_nodes.append(sib)

            if tail_nodes:
                out["ending_hook"]["html"], out["ending_hook"]["text"] = _html_and_text(tail_nodes)
            else:
                # If there was no UL (edge case), fall back to "after heading" behavior but
                # skip the first non-heading block if it's clearly the details content.
                pass  # keep empty if nothing sensible is found


    return out

def extract_parts(
    html: str,
    parts: Optional[Iterable[str]] = None,
    include_heading: bool = True,
    as_text: bool = False,
) -> Dict[str, str]:
    """
    Convenience wrapper to return only selected parts as HTML or plain text.
    parts can be any subset of:
        {"title_block", "story_behind", "print_details", "ending_hook"}
    """
    parsed = parse_description_sections(html, include_heading=include_heading)
    if parts is None:
        parts = ["title_block", "story_behind", "print_details", "ending_hook"]
    parts = list(parts)

    result = {}
    for key in parts:
        if key not in parsed:
            continue
        if as_text:
            result[key] = parsed[key].get("text", "")
        else:
            result[key] = parsed[key].get("html", "")
    return result


## HOW TO USE EXTACT DESCRIPTION EXAMPLE
# product_description_html = "SOME HTML EXAMPLE OF THE DESCRIPTION"
# parts = extract_parts(
#     product_description_html,
#     parts=["print_details"],      # or any subset: ["story_behind","ending_hook"], etc.
#     include_heading=True,         # keep or drop the <h2> heading
#     as_text=False                 # return HTML (False) or plain text only (True)
# )
# print(parts["print_details"])     # HTML fragment for Print Details (+ ending paragraph if present)

# # Need just the bullet list as Python strings?
# parsed = parse_description_sections(product_description_html)
# print(parsed["print_details"].get("bullets", []))
# parsed = parse_description_sections(product_description_html, include_heading=True)
# print(parsed["print_details"]["html"])      # HTML fragment
# print(parsed["print_details"]["text"])      # plain text
# print(parsed["print_details"]["bullets"])   # list of bullet strings


## MY TESTING 
# product_data_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/product_data/the-stranger-meursault-print-11x14-karla-white-black.json"
# with open(product_data_path, 'r') as f:
#     product_data = json.load(f)

# product_description = product_data['product_description_html']
# parsed = parse_description_sections(product_description)
# print("TITLE BLOCK HTML")
# print(parsed["title_block"]["html"])      # HTML fragment
# print()
# print("STORY BEHIND HTML")
# print(parsed["story_behind"]["html"])      # HTML fragment
# print()
# print("PRINT DETAILS HTML")
# print(parsed["print_details"]["html"])      # HTML fragment
# print()
# print("ENDING HOOK HTML")
# print(parsed["ending_hook"]["html"])      # HTML fragment