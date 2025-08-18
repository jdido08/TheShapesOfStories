import base64
import mimetypes
import json
import os
from llm import load_config, get_llm, extract_json
from langchain_core.messages import HumanMessage

# --- Configuration ---
# Ensure this path is correct for your system
config_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml'
llm_provider = 'anthropic'
# Using a powerful model capable of complex visual reasoning and instruction following
llm_model = 'claude-sonnet-4-20250514' #'gpt-5-2025-08-07'#'gemini-2.5-pro'

# --- Helper Functions (copied from your example) ---

def encode_image(image_path: str) -> str:
    """Encodes an image file into a Base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def get_image_mime_type(image_path: str) -> str:
    """Gets the MIME type of an image file."""
    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type is None:
        raise ValueError(f"Could not determine MIME type for {image_path}")
    return mime_type

# --- Main Categorization Function ---

def categorize_shape_visually(image_path: str):
    """
    Analyzes a story shape image using a multimodal LLM and classifies it
    according to Vonnegut's archetypes and relative emotional magnitude.
    """
    if not os.path.exists(image_path):
        print(f"Error: Image path not found at {image_path}")
        return
    
    # if not os.path.exists(story_data_path):
    #     print(f"Error: Story data file not found at {story_data_path}")
    #     return
    # if not os.path.exists(image_path):
    #     print(f"Error: Image path not found at {image_path}")
    #     return

    # with open(story_data_path, 'r') as f:
    #     story_data = json.load(f)

    # # --- 2. Extract Variables for the Prompt ---
    # title = story_data.get("title", "this story")
    # author = story_data.get("author_name", "the author") 
    # protagonist = story_data.get("protagonist", "the protagonist")

    # The refined, truly relative multimodal prompt

#     prompt_template = f"""
#     Analyze the curve shown in this image using pure geometric shape analysis.

#     ---
#     ## 1. IMAGE STRUCTURE
#     The uploaded image contains several elements:
#     **FOCUS ON:** The CURVE LINE that traces a path across the image
#     **IGNORE COMPLETELY:** 
#     - The characters/text which make up the CURVE LINE 
#     - All text at the bottom (title, author name, character name)
#     - Background color
#     - Any decorative elements
#     - Image borders or formatting


#     ---
#     ## 2. VISUAL ANALYSIS INSTRUCTIONS

#     **STEP 1: IDENTIFY CURVE COMPONENTS**
#     - Trace the entire curve, starting at the leftmost point and follow the curve to the rightmost point
#     - Identify each core curve component i.e. EVERY significant directional change
#     - Assign one of the following directional changes to each curve
#         - up (`→`): Change upwards
#         - down (`↓`): Change downwards
#         - flat (`→`): Minimal vertical change, mostly horizontal

#     **STEP 2: COMPARE RELATIVE MAGNITUDES**
#     - Look at the magnitude (i.e. HEIGHT and STEEPNESS) of curve component
#     - Measure the magnitude of each curve comonent vs each other 
#     - Assign one of the following sizes to each component magnitude
#         -   **Standard (1 arrow: `↑` or `↓`):** Baseline noticeable movement
#         -   **Major (2 arrows: `↑↑` or `↓↓`):** Clearly larger than standard movements but not overwhelming  
#         -   **Epic (3 arrows: `↑↑↑` or `↓↓↓`):** Dominates the entire visual - much larger than everything else

#     **CRITICAL**: 
#     If there are multiple components of the curve and all the components in a curve are of a roughly similar in magnitude, then they are **all** standard size.
#     A curve needs a clear distinction in the magnotides between its components to warrant the use of major or epic shifts.


#     **STEP 3: CREATE SYMBOLIC STRING**
#     - List each major phase in chronological order (left to right)
#     - Separate with single spaces: `↑ ↓↓ ↑`

#     ---
    
#     ## 3. OUTPUT FORMAT
#     Respond ONLY in the following JSON format. Do not add any other text or explanation.

#     ```json
#     {{
#     "shape_category": {{
#         "symbolic_representation": "Your pattern (e.g., '↑ ↓↓ ↑')",
#         "justification": "One sentence explaining how the visual pattern matches the archetype, referencing specific curve segments."
#     }}
#     }}
#     ```
#     """

#     prompt_template = f""" 
# Analyze ONLY the solid story curve. Ignore all text, colors, borders, axes, and decorations.

# GOAL
# Reduce the curve to MAJOR monotonic segments left→right.

# SEGMENTATION RULES
# - MAX 4 segments total; prefer simpler sequences when ambiguous.
# - A direction change counts only if PROMINENCE ≥ 0.12 of total vertical range.
#   (prominence = |Δy| / (y_max − y_min))
# - FLAT (→) allowed only if vertical change < 0.08 of total range over ≥ 0.15 of image width.
# - Merge short blips into neighboring segments.

# RELATIVE MAGNITUDES (contrast within THIS image)
# - For each segment, compute Δy_norm = |Δy| / (y_max − y_min).
# - Let M_max = max(Δy_norm), M_med = median(Δy_norm).

# Use intensity arrows ONLY to signal contrast:
# - If M_max / M_med < 1.4 → segments are similar → use single arrows only.
# - Otherwise, assign levels relative to M_med:
#   • Standard:   0.12 ≤ Δy_norm < 1.5×M_med → ↑ or ↓
#   • Major:      1.5×M_med ≤ Δy_norm < 2.2×M_med → ↑↑ or ↓↓
#   • Epic:       Δy_norm ≥ 2.2×M_med AND Δy_norm ≥ 0.45 → ↑↑↑ or ↓↓↓

# GUARDS
# - At most 1 epic; if tie, mark the longest segment epic and demote others to major.
# - With exactly 2 segments, NEVER use ↑↑/↓↓/↑↑↑/↓↓↓ (only single arrows).
# - Never assign the same intensity to all segments; if that would happen, downgrade all to single.
# - If unsure on segmentation or intensity, choose the simpler (fewer segments, smaller intensity).

# OUTPUT (RAW JSON ONLY — no backticks). Allowed symbols EXACTLY: ↑ ↓ →.
# Return:
# {{
#   "shape_category": {{
#     "symbols": "<compact string without spaces, e.g., \"↑↓↓↑\" or \"↓↑\">",
#     "symbols_spaced": "<same with single spaces, e.g., \"↑ ↓↓ ↑\">",
#     "base": "<collapse repeats; drop leading/trailing →, e.g., \"↑↓↑\">",
#     "breakpoints": [<x positions from 0 to 1 where segments meet, include 0 and 1>],
#     "confidence": <0.0–1.0>,
#     "rationale": "<≤ 20 words about the major segments only>"
#   }}
# }}
    
#     """

    prompt_template = """
    You convert a single plotted narrative curve into a symbolic arrow grammar.

FOCUS: the single solid curve running left→right.
IGNORE: any letters drawn along the curve, titles/names at the bottom, borders, colors, axes, or decorations. This task is about the curve’s geometry only.

SEGMENTATION
- Work strictly left→right.
- Split the curve into monotonic segments: rising (↑), falling (↓), or flat (→).
- Count a direction change only when the change is visibly prominent; ignore tiny wiggles.
- Prefer simplicity: merge adjacent segments with the same direction and similar magnitude.
- Avoid over-segmentation: each returned segment should span a non-trivial horizontal extent (≈ ≥ 0.07 of width).

MAGNITUDES (COARSE, VISUAL)
- Assign each non-flat segment a size bucket: tiny, small, medium, or large, based on the **visual** proportion of vertical change relative to the curve’s overall vertical range.
- Treat `tiny` up/down segments as flat (→) in the final symbolic string.
- Map bucket → arrows for each non-flat segment:
    small  → one arrow (↑ or ↓)
    medium → two arrows (↑↑ or ↓↓)
    large  → three arrows (↑↑↑ or ↓↓↓)
- NOTE: If there are multiple segments of the curve and all the segments in a curve are of a roughly similar in magnitude, then they are **all** 'small'. A curve needs a clear distinction in the segment mangitudes to warrant the use of medium or large.


FLAT
- Use flat (→) when the curve stays roughly level over a noticeable span.
- Short level sections embedded in a longer rise/fall need not become separate flat segments.

OUTPUT
- Return strict JSON only (no code fences), describing segments, the final symbolic string, a confidence, and one-sentence justification that references early/mid/late structure.

Required JSON shape:
{
  "segments": [
    {
      "dir": "up|down|flat",
      "x0": 0.00-1.00,
      "x1": 0.00-1.00,
      "magnitude_bucket": "tiny|small|medium|large",   // for up/down; use "tiny" or omit for flat
      "arrows": "→|↑|↑↑|↑↑↑|↓|↓↓|↓↓↓"
      // Optional hint the model may include:
      "dy_norm_guess": 0.00-1.00
    }
    // 2..N items; x0 of first = 0; x1 of last = 1; strictly increasing
  ],
  "symbolic": "e.g., \"↓ → ↑↑\"",
  "confidence": 0.00-1.00,
  "justification": "One sentence pointing to early/mid/late features that drove the decision."
}
    """


    # --- Encode the Image ---
    base64_image = encode_image(image_path)
    image_mime_type = get_image_mime_type(image_path)

    # --- Construct the Multimodal Message ---
    message = HumanMessage(
        content=[
            {
                "type": "text",
                "text": prompt_template,
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_mime_type};base64,{base64_image}"
                }
            },
        ]
    )

    # --- Initialize and Invoke LLM ---
    print("Initializing LLM and sending request...")
    config = load_config(config_path=config_path)
    
    # Note: Setting max_tokens for a JSON output is a good safeguard
    llm = get_llm(llm_provider, llm_model, config, max_tokens=1024)
    
    response = llm.invoke([message])
    
    # --- Process and Print the Response ---
    print("\n--- Raw LLM Response ---")
    print(response.content)

    print("\n--- Parsed JSON Output ---")
    try:
        # Use extract_json to handle potential markdown formatting (e.g., ```json ... ```)
        parsed_json = extract_json(response.content)
        # Pretty-print the final JSON
        print(json.dumps(parsed_json, indent=2))
        return parsed_json
    except (json.JSONDecodeError, ValueError) as e:
        print(f"Error: Failed to parse JSON from LLM response. Error: {e}")
        return None


# def find_story_archetype():

#     # ---
    # ## 3. ARCHETYPE MATCHING

    # **RULES: 
    # 1. Count the number of directional changes in your symbolic representation
    # 2. Match to the corresponding category below  
    # 3. **DOUBLE-CHECK:** Does your symbolic representation actually match your chosen archetype's template?


    # ### 1-PART PATTERNS (No directional changes):
    # -   **Rags to Riches:** `↑` (any single upward: `↑`, `↑↑`, `↑↑↑`)
    # -   **From Bad to Worse:** `↓` (any single downward: `↓`, `↓↓`, `↓↓↓`)

    # ### 2-PART PATTERNS (One directional change):
    # -   **Man in Hole:** `↓ ↑` (any magnitude combination like `↓↓ ↑` or `↓ ↑↑`)
    #     - Must start with decline, end with recovery
    # -   **Icarus:** `↑ ↓` (any magnitude combination like `↑↑ ↓` or `↑ ↓↓`)  
    #     - Must start with rise, end with fall, NO recovery

    # ### 3-PART PATTERNS (Two directional changes):
    # -   **Boy Meets Girl:** `↑ ↓ ↑` (any magnitude like `↑↑ ↓↓ ↑` or `↑ ↓ ↑↑`)
    #     - Must be: rise → fall → recovery (final movement can be any size)

    # ### 4-PART PATTERNS (Three directional changes):
    # -   **Cinderella:** `→ ↑ ↓ ↑` where final `↑` is larger than first `↑`
    #     - Must have: stasis → rise → fall → BIGGER recovery

    # ### COMPLEX PATTERNS:
    # -   **Other:** 5+ parts OR patterns that don't fit any template above

    # ---




# --- Script Execution ---
if __name__ == "__main__":
    # Path to the image you want to analyze
    # IMAGE_FILE = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-for-whom-the-bell-tolls_protagonist-robert-jordan_product-print_size-8x10_line-type-char_background-color-#3B4A3B_font-color-#F3F0E8_border-color-FFFFFF_font-Merriweather_title-display-yes.png'
    # IMAGE_FILE ='/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-pride-and-prejudice_protagonist-elizabeth-bennet_product-print_size-8x10_line-type-char_background-color-#1B365D_font-color-#F5E6D3_border-color-FFFFFF_font-Baskerville_title-display-yes.png'
    IMAGE_FILE = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-the-great-gatsby_protagonist-jay-gatsby_product-print_size-8x10_line-type-char_background-color-#0A1F3B_font-color-#F9D342_border-color-FFFFFF_font-Josefin Sans_title-display-yes.png'
    #IMAGE_FILE = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-pride-and-prejudice_protagonist-elizabeth-bennet_product-print_size-8x10_line-type-line_background-color-#1B365D_font-color-#F5E6D3_border-color-FFFFFF_font-Baskerville_title-display-yes.png'


    #STORY_DATA_FILE = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-great-gatsby_jay-gatsby.json'
    #STORY_DATA_FILE = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/for-whom-the-bell-tolls_robert-jordan_8x10.json'
    #STORY_DATA_FILE = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/pride-and-prejudice_elizabeth-bennet.json'
    
    categorize_shape_visually(
        #story_data_path=STORY_DATA_FILE, 
        image_path=IMAGE_FILE
    )
