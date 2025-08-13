# categorize_shape.py

import json
import os
from datetime import datetime
from llm import load_config, get_llm, extract_json
from langchain.prompts import PromptTemplate

def get_shape_category_from_llm(config_path: str, generated_analysis: dict, llm_provider: str, llm_model: str) -> dict:
    """
    Uses an LLM to categorize a story's emotional shape into a Vonnegut-style archetype.

    Args:
        config_path (str): Path to the LLM configuration file.
        generated_analysis (dict): The full story data JSON.
        llm_provider (str): The LLM provider to use.
        llm_model (str): The specific LLM model to use.

    Returns:
        dict: A dictionary containing the shape archetype, symbolic representation, and justification.
    """
    # --- 1. Prepare Inputs for the Prompt ---
    # We only need the emotional scores and timestamps to analyze the pure shape.
    emotional_trajectory = []
    for component in generated_analysis.get("story_components", []):
        emotional_trajectory.append({
            "end_time": component.get("end_time"),
            "end_emotional_score": component.get("end_emotional_score")
        })

    analysis_to_categorize = {
        "title": generated_analysis.get("title"),
        "protagonist": generated_analysis.get("protagonist"),
        "emotional_trajectory": emotional_trajectory
    }
    generated_analysis_str = json.dumps(analysis_to_categorize, indent=2)

    # Extract other details for the prompt context
    title = generated_analysis.get("title", "this story")
    protagonist = generated_analysis.get("protagonist", "the protagonist")

    # --- 2. Define the Categorization Prompt ---
    prompt_template = """
You are a master literary cartographer, an expert in mapping the emotional journeys of stories according to Kurt Vonnegut's theory of story shapes. Your task is to analyze a protagonist's emotional trajectory and classify it into a specific narrative archetype, complete with a symbolic representation that captures its emotional magnitude and pacing.

---
## 1. STORY DATA TO ANALYZE

This JSON contains the emotional trajectory for {protagonist} from the story "{title}". The `emotional_trajectory` shows the protagonist's emotional score (from -10 for ultimate despair to +10 for ultimate euphoria) at key moments (`end_time` from 0 to 100).

{generated_analysis}

---
## 2. THE VONNEGUT ARCHETYPES (Classification Rubric)

You must classify the story's overall shape into the **best-fitting** archetype from this specific list.

- **Man in Hole (↓↑):** The protagonist starts well, falls into significant trouble, and then climbs out, often ending better off.
- **Boy Meets Girl (↑↓↑):** The protagonist finds something wonderful, loses it, and then struggles to regain it, culminating in success.
- **Icarus (↑↓):** The protagonist has a swift rise in fortune, followed by a sudden, ruinous fall.
- **Rags to Riches (↑):** A continuous, sustained rise from a low point to a high point.
- **From Bad to Worse / Tragedy (↓):** A steady decline from a relatively high position into disaster.
- **Cinderella (→↑↓↑):** A more complex shape involving multiple turns: a low-starting point (stasis), a magical rise to joy, a sudden setback, and a final, triumphant resolution.
- **Complex / Other (N/A):** Use only if the shape has no clear overall direction or defies all other classifications.

---
## 3. SYMBOLIC REPRESENTATION (Magnitude & Pacing Analysis)

After choosing an archetype, you must create a symbolic string (e.g., "↓↑↑"). This representation must capture not only the **magnitude** of each emotional shift but also its **pacing** (how quickly it happens).

**Follow these hierarchical rules to build the symbol string:**
1.  **Identify Movements:** Break the trajectory into its core directional movements (e.g., a fall, then a rise).
2.  **Assign Symbols based on Steepness:** For each movement, calculate the change in emotion and the change in time, then apply the following rules in order:

    -   **Stasis (→):** A minimal emotional change (from -1 to +1 points, including 0), regardless of time. This represents stability or a holding pattern.

    -   **Epic/Catastrophic Shift (3 Arrows: `↑↑↑` or `↓↓↓`):**
        A *large* emotional change (8+ points) that occurs *suddenly* (over 25 or fewer timeline points). This represents the most dramatic, life-altering moments.

    -   **Major Shift (2 Arrows: `↑↑` or `↓↓`):**
        This applies to either of two conditions:
        - A *significant* change (4-7 points) that occurs *suddenly* (over 25 or fewer timeline points).
        - A *large* change (8+ points) that occurs *gradually* (over more than 25 timeline points).

    -   **Standard Shift (1 Arrow: `↑` or `↓`):**
        Any other rise or fall. This typically applies to minor changes (1-3 points) or very slow, drawn-out shifts in fortune.

3.  **Combine:** Join the symbols in chronological order to create the final string. **Ensure there is a single space between each distinct movement.**

**Example Analysis:** A trajectory of `(time:0, score:2) -> (time:15, score:-7) -> (time:80, score:9)` would be:
-   **Movement 1:** Fall of 9 points (`-9`) over 15 timeline points. Symbol: `↓↓↓`
-   **Movement 2:** Rise of 16 points (`+16`) over 65 timeline points. Symbol: `↑↑`
-   **Final Symbolic Representation:** `↓↓↓ ↑↑`

---
## 4. INSTRUCTIONS & OUTPUT FORMAT

Analyze the `emotional_trajectory`. First, determine the best-fitting `archetype`. Second, perform the magnitude and pacing analysis to create the `symbolic_representation`. Finally, provide a concise justification.

Provide your answer ONLY in the following JSON format.

```json
{{
  "shape_category": {{
    "archetype": "Name of the Archetype",
    "symbolic_representation": "The final symbol string (e.g., '↓↓ ↓↑↑')",
    "justification": "A concise, one-sentence explanation linking the archetype and the symbolic representation to the key turning points of the protagonist's journey."
  }}
}}
"""
    prompt = PromptTemplate(
        input_variables=["generated_analysis", "title", "protagonist"],
        template=prompt_template
    )
    config = load_config(config_path=config_path)
    # Using a capable model is important for this reasoning task
    llm = get_llm(llm_provider, llm_model, config)
    runnable = prompt | llm

    output = runnable.invoke({
        "generated_analysis": generated_analysis_str,
        "title": title,
        "protagonist": protagonist
    })

    print("OUTPUT")
    print(output)

    if hasattr(output, "content"):
        output_text = output.content
    else:
        output_text = output

    # --- ADD THIS LINE FOR DEBUGGING ---
    print("--- RAW LLM OUTPUT ---\n" + output_text + "\n----------------------")
        
    extracted_text = extract_json(output_text)

    try:
        category_dict = json.loads(extracted_text)
    except (json.JSONDecodeError, TypeError) as e:
        print(f"Error parsing JSON from LLM output: {e}")
        print(f"Raw extracted text was: {extracted_text}")
        return {"error": "Failed to parse LLM response as JSON."}
        
    print("--- Shape Category Output (Parsed) ---")
    print(json.dumps(category_dict, indent=2))
    print("------------------------------------")

    return category_dict

def categorize_story_shape(generated_analysis_path: str, config_path: str = 'config.yaml'):
    """
    Orchestrates the categorization of a story's shape and updates the source JSON file.
    Args:
        generated_analysis_path (str): The file path to the story data JSON.
        config_path (str, optional): Path to the LLM configuration file.
    """
    print(f"--- Starting Shape Categorization for {os.path.basename(generated_analysis_path)} ---")

    if not os.path.exists(generated_analysis_path):
        print(f"Error: Analysis file not found at {generated_analysis_path}")
        return

    with open(generated_analysis_path, 'r') as f:
        generated_analysis = json.load(f)

    # Use a powerful model for this analytical step.
    # claude-3-5-sonnet-latest or gemini-2.5-pro are good choices.
    categorizer_llm_provider =  'anthropic'
    categorizer_llm_model = 'claude-3-5-sonnet-latest'

    try:
        category_result = get_shape_category_from_llm(
            config_path=config_path,
            generated_analysis=generated_analysis,
            llm_provider=categorizer_llm_provider,
            llm_model=categorizer_llm_model
        )
    except Exception as e:
        print(f"An error occurred during the categorization step: {e}")
        # Log the failure to the file
        generated_analysis['shape_category'] = {
            "status": "categorization_error",
            "error_message": str(e),
            "categorization_timestamp": datetime.now().isoformat()
        }
        with open(generated_analysis_path, 'w') as f:
            json.dump(generated_analysis, f, indent=4)
        return

    # Add the categorization results to the main dictionary
    # The result from the LLM is nested under 'shape_category', so we extract that inner object
    if 'shape_category' in category_result:
        generated_analysis['shape_category'] = category_result['shape_category']
        generated_analysis['shape_category']['categorization_timestamp'] = datetime.now().isoformat()
        generated_analysis['shape_category']['categorization_model'] = categorizer_llm_model
    else:
        # Handle cases where the LLM might have returned an error or unexpected format
        generated_analysis['shape_category'] = {
            "status": "categorization_failed",
            "details": category_result,
            "categorization_timestamp": datetime.now().isoformat()
        }

    # Write the enriched data back to the original file
    with open(generated_analysis_path, 'w') as f:
        json.dump(generated_analysis, f, indent=4)
        
    print(f"Successfully updated {os.path.basename(generated_analysis_path)} with shape category.")



categorize_story_shape(
    generated_analysis_path='/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/pride-and-prejudice_elizabeth-bennet.json'
)