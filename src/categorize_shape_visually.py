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

def categorize_shape_visually(story_data_path: str, image_path: str):
    """
    Analyzes a story shape image using a multimodal LLM and classifies it
    according to Vonnegut's archetypes and relative emotional magnitude.
    """
    if not os.path.exists(image_path):
        print(f"Error: Image path not found at {image_path}")
        return
    
    if not os.path.exists(story_data_path):
        print(f"Error: Story data file not found at {story_data_path}")
        return
    if not os.path.exists(image_path):
        print(f"Error: Image path not found at {image_path}")
        return

    with open(story_data_path, 'r') as f:
        story_data = json.load(f)

    # --- 2. Extract Variables for the Prompt ---
    title = story_data.get("title", "this story")
    author = story_data.get("author_name", "the author") 
    protagonist = story_data.get("protagonist", "the protagonist")

    # The refined, truly relative multimodal prompt
    
    prompt_template = f"""
    You are a master literary cartographer analyzing the emotional journey curve in the uploaded image. 

    ---
    ## 1. STORY SHAPE TO ANALYZE
    The uploaded image shows the emotional journey of {protagonist} from {author}'s {title}.

    ---
    ## 2. VISUAL ANALYSIS INSTRUCTIONS

    **STEP 1: TRACE THE ENTIRE CURVE**
    - Start at the leftmost point and follow the curve to the rightmost point
    - Identify EVERY significant directional change (up→down, down→up, flat→up, etc.)

    **STEP 2: COMPARE RELATIVE MAGNITUDES**
    Look at the magnitude (i.e. HEIGHT and STEEPNESS) of each movement on the story shape:
    
    -   **Standard Shift (1 arrow: `↑` or `↓`):** Baseline noticeable movement
    -   **Major Shift (2 arrows: `↑↑` or `↓↓`):** Clearly larger than standard movements but not overwhelming  
    -   **Epic Shift (3 arrows: `↑↑↑` or `↓↓↓`):** Dominates the entire visual - much larger than everything else
    -   **Stasis (`→`):** Minimal vertical change, mostly horizontal

    **CRITICAL**: 
    If there are multiple shifts in the story shape and all the shifts in a story are of a roughly similar in magnitude, then they are **all** standard shifts.
    A story needs a clear distinction in the magnotide between its movements to warrant the use of major or epic shifts.


    **STEP 3: CREATE SYMBOLIC STRING**
    - List each major phase in chronological order (left to right)
    - Separate with single spaces: `↑ ↓↓ ↑`
    - If unsure between magnitudes, choose the smaller symbol.

    ---
    ## 3. ARCHETYPE MATCHING

    **RULES: 
    1. Count the number of directional changes in your symbolic representation
    2. Match to the corresponding category below  
    3. **DOUBLE-CHECK:** Does your symbolic representation actually match your chosen archetype's template?


    ### 1-PART PATTERNS (No directional changes):
    -   **Rags to Riches:** `↑` (any single upward: `↑`, `↑↑`, `↑↑↑`)
    -   **From Bad to Worse:** `↓` (any single downward: `↓`, `↓↓`, `↓↓↓`)

    ### 2-PART PATTERNS (One directional change):
    -   **Man in Hole:** `↓ ↑` (any magnitude combination like `↓↓ ↑` or `↓ ↑↑`)
        - Must start with decline, end with recovery
    -   **Icarus:** `↑ ↓` (any magnitude combination like `↑↑ ↓` or `↑ ↓↓`)  
        - Must start with rise, end with fall, NO recovery

    ### 3-PART PATTERNS (Two directional changes):
    -   **Boy Meets Girl:** `↑ ↓ ↑` (any magnitude like `↑↑ ↓↓ ↑` or `↑ ↓ ↑↑`)
        - Must be: rise → fall → recovery (final movement can be any size)

    ### 4-PART PATTERNS (Three directional changes):
    -   **Cinderella:** `→ ↑ ↓ ↑` where final `↑` is larger than first `↑`
        - Must have: stasis → rise → fall → BIGGER recovery

    ### COMPLEX PATTERNS:
    -   **Other:** 5+ parts OR patterns that don't fit any template above

    ---

    ## 4. OUTPUT FORMAT
    Respond ONLY in the following JSON format. Do not add any other text or explanation.

    ```json
    {{
    "shape_category": {{
        "symbolic_representation": "Your pattern (e.g., '↑ ↓↓ ↑')",
        "archetype": "Exact archetype name",
        "justification": "One sentence explaining how the visual pattern matches the archetype, referencing specific curve segments."
    }}
    }}
    ```
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

# --- Script Execution ---
if __name__ == "__main__":
    # Path to the image you want to analyze
    #IMAGE_FILE = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-for-whom-the-bell-tolls_protagonist-robert-jordan_product-print_size-8x10_line-type-char_background-color-#3B4A3B_font-color-#F3F0E8_border-color-FFFFFF_font-Merriweather_title-display-yes.png'
    IMAGE_FILE ='/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-pride-and-prejudice_protagonist-elizabeth-bennet_product-print_size-8x10_line-type-char_background-color-#1B365D_font-color-#F5E6D3_border-color-FFFFFF_font-Baskerville_title-display-yes.png'
    #IMAGE_FILE = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-the-great-gatsby_protagonist-jay-gatsby_product-print_size-8x10_line-type-char_background-color-#0A1F3B_font-color-#F9D342_border-color-FFFFFF_font-Josefin Sans_title-display-yes.png'
    
    #STORY_DATA_FILE = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-great-gatsby_jay-gatsby.json'
    #STORY_DATA_FILE = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/for-whom-the-bell-tolls_robert-jordan_8x10.json'
    STORY_DATA_FILE = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/pride-and-prejudice_elizabeth-bennet.json'
    
    categorize_shape_visually(
        story_data_path=STORY_DATA_FILE, 
        image_path=IMAGE_FILE
    )
