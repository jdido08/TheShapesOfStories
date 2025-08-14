import base64
import mimetypes
import json
import os
from llm import load_config, get_llm, extract_json
from langchain_core.messages import HumanMessage

# --- Configuration ---
# Ensure this path is correct for your system
config_path = '/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml'
llm_provider = 'google'
# Using a powerful model capable of complex visual reasoning and instruction following
llm_model = 'gemini-2.5-pro' 

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

    # The refined, truly relative multimodal prompt
    prompt_template = """
    You are a master literary cartographer, an expert in mapping the emotional journeys of stories. Your task is to analyze the provided image of a story's emotional graph.

    Based on the visual shape of the graph, you will:
    1.  Classify it into the best-fitting Vonnegut archetype.
    2.  Create a symbolic representation that captures the **truly relative magnitude** of each emotional shift.
    3.  Provide a concise justification for your analysis.

    **Core Principle: Your analysis must be fully relative.** Compare all shifts within the story **to each other**. Not all stories will use multiple arrow types. A story with modest, similar-sized movements might only use single arrows (`↑`, `↓`). The goal is to reflect the story's unique emotional volatility.

    ---
    ## 1. STORY SHAPE TO ANALYZE

    (The user will upload the story shape image here.)

    ---
    ## 2. THE VONNEGUT ARCHETYPES (Classification Rubric)

    Classify the story's overall visual shape into the **best-fitting** archetype from this list.

    -   **Man in Hole (↓ ↑):** Starts well, falls into trouble, and then climbs out.
    -   **Boy Meets Girl (↑ ↓ ↑):** Finds something wonderful, loses it, and then regains it.
    -   **Icarus (↑ ↓):** A rise in fortune, followed by a ruinous fall.
    -   **Rags to Riches (↑):** A continuous, sustained rise from a low point to a high point.
    -   **Tragedy / From Bad to Worse (↓):** A steady decline from a relatively high position into disaster.
    -   **Cinderella (→ ↑ ↓ ↑):** A low start, a big rise, a setback, and a final, even bigger rise.
    -   **Complex / Other:** The shape has no clear overall direction or defies other classifications.

    ---
    ## 3. RELATIVE MAGNITUDE ANALYSIS (Visual Instructions)

    Create a symbolic string by visually grouping all emotional shifts (rises and falls) into tiers of magnitude **relative to each other**.

    -   **Standard Shift (1 Arrow: `↑` or `↓`):**
        This is the baseline symbol for a noticeable emotional movement. If all shifts in a story are of a roughly similar, modest magnitude, they will **all** receive this symbol.

    -   **Major Shift (2 Arrows: `↑↑` or `↓↓`):**
        Use this for shifts that are **visually and significantly larger** than the "Standard" shifts *within the same story*. A story needs a clear distinction in size between its movements to warrant using this symbol.

    -   **Epic Shift (3 Arrows: `↑↑↑` or `↓↓↓`):**
        Use this **only** for a shift that is in a class of its own—one that **visually dwarfs** even the "Major" shifts. It should be exceptionally rare, used only when one movement defines the entire emotional landscape of the story.

    -   **Stasis (→):**
        A phase with **minimal or no vertical change**.

    **Combine:** Join the symbols for each major phase in chronological order, separated by a single space. For example: `↑ ↓↓ ↑↑↑`.

    ---
    ## 4. YOUR TASK & OUTPUT FORMAT

    Analyze the user-provided image. Determine the best-fitting `archetype` and the `symbolic_representation` based on a truly relative visual analysis.

    Provide your answer ONLY in the following JSON format. Do not add any other text or explanation.

    ```json
    {
      "shape_category": {
        "archetype": "Name of the Archetype",
        "symbolic_representation": "The final symbol string (e.g., '↑ ↓↓')",
        "justification": "A concise, one-sentence explanation linking the archetype and the symbolic representation to the key visual turning points of the protagonist's journey."
      }
    }
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
    image_to_analyze = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_shapes/title-for-whom-the-bell-tolls_protagonist-robert-jordan_product-print_size-8x10_line-type-char_background-color-#3B4A3B_font-color-#F3F0E8_border-color-FFFFFF_font-Merriweather_title-display-yes.png'
    
    categorize_shape_visually(image_to_analyze)