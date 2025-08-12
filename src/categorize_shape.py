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
You are a literary analyst specializing in narrative archetypes, based on Kurt Vonnegut's theories on the shapes of stories. Your task is to analyze the emotional trajectory of a protagonist and classify it into one of the common story shapes.

---
## STORY DATA TO ANALYZE

This JSON contains the emotional trajectory for {protagonist} from the story "{title}". The `emotional_trajectory` shows the protagonist's emotional score (from -10 for despair to +10 for euphoria) at different points in the story (`end_time` from 0 to 100).

{generated_analysis}

---
## STORY SHAPE ARCHETYPES (Your Rubric)

You must classify the story into the **best-fitting** archetype from the list below.

1.  **Man in Hole**
    -   **Symbol:** ↓↑
    -   **Description:** The protagonist starts off well, falls into trouble, and then gets out of it, often ending up better than before.

2.  **Boy Meets Girl**
    -   **Symbol:** ↑↓↑
    -   **Description:** The protagonist finds something wonderful (a person, a goal), loses it, and then gets it back in the end. A story of finding, losing, and regaining.

3.  **From Bad to Worse (Tragedy)**
    -   **Symbol:** ↓
    -   **Description:** A steady decline from a relatively high position into ruin and disaster. The protagonist's fortune consistently worsens.

4.  **Rags to Riches**
    -   **Symbol:** ↑
    -   **Description:** A steady, continuous rise from a state of low fortune to one of high fortune and success.

5.  **Icarus**
    -   **Symbol:** ↑↓
    -   **Description:** The protagonist experiences a rapid rise to success or happiness, only to be followed by a sudden and dramatic fall.

6.  **Cinderella**
    -   **Symbol:** →↑↓↑
    -   **Description:** The story features several distinct emotional shifts, often starting from a low point, rising to joy, suffering a setback, and then achieving a final, ultimate triumph. This shape has more complexity than "Man in Hole."

7.  **Complex/Other**
    -   **Symbol:** N/A
    -   **Description:** Use this category if the story's shape does not clearly fit any of the archetypes above. This could be due to a flat emotional arc, multiple complex oscillations, or other unique structures.

---
## INSTRUCTIONS & OUTPUT FORMAT

Analyze the `emotional_trajectory` and determine which archetype it most closely represents. Provide your answer ONLY in the following JSON format.

```json
{{
  "shape_category": {{
    "archetype": "Name of the Archetype",
    "symbolic_representation": "Symbol for the Archetype (e.g., ↓↑)",
    "justification": "A concise, one-sentence explanation for why you chose this category, referencing the emotional trajectory provided."
  }}
}}
"""
    prompt = PromptTemplate(
    input_variables=["generated_analysis", "title", "protagonist"],
    template=prompt_template
    )
    config = load_config(config_path=config_path)
    # Using a capable model is important for this reasoning task
    llm = get_llm(llm_provider, llm_model, config, max_tokens=1024)
    runnable = prompt | llm

    output = runnable.invoke({
        "generated_analysis": generated_analysis_str,
        "title": title,
        "protagonist": protagonist
    })

    if hasattr(output, "content"):
        output_text = output.content
    else:
        output_text = output
        
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
    categorizer_llm_provider = 'anthropic'
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