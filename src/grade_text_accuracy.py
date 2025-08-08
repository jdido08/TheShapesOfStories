#`grade_text_accuracy.py`
#This file is responsible **only** for checking if the `arc_text` is a good summary of the `description` from which it was generated (Internal Consistency). It does **not** need the canonical summary.

from llm import load_config, get_llm, extract_json
from langchain.prompts import PromptTemplate
import json

def grade_text_accuracy(config_path: str, generated_analysis: dict, llm_provider: str, llm_model: str) -> dict:
    """
    Grades the accuracy of the artwork text (Internal Consistency).

    Compares the generated `arc_text` in each story component against its
    source `description` to ensure it is an accurate and effective summary.

    Args:
        config_path (str): Path to the LLM configuration file.
        generated_analysis (dict): The generated story JSON, containing descriptions and arc_text.
        llm_provider (str): The LLM provider to use.
        llm_model (str): The specific LLM model to use (e.g., 'gpt-4-turbo').

    Returns:
        dict: A dictionary containing the artwork_text_accuracy grade and justification.
    """

    # --- 1. Prepare Inputs for the Prompt ---
    simplified_components = []
    for component in generated_analysis.get("story_components", []):
        if component.get("arc_text"): # Only include components with text to grade
            simplified_components.append({
                "description": component.get("description"),
                "arc_text": component.get("arc_text")
            })

    analysis_to_grade = {
        "title": generated_analysis.get("title"),
        "protagonist": generated_analysis.get("protagonist"),
        "components_to_grade": simplified_components
    }
    generated_analysis_str = json.dumps(analysis_to_grade, indent=4)

    # --- 2. Define the Prompt Template ---
    prompt_template = """
You are a meticulous literary analyst and a quality assurance expert for "The Shapes of Stories." Your task is to critically review and grade the generated artwork text for its internal consistency.

---
## INPUT DATA

### Generated Story Components (JSON)
{generated_analysis}

---
## ASSESSMENT TASK & INSTRUCTIONS

### Assess Artwork Text Accuracy (Internal Consistency)

**Instructions:**
1.  **Use ONLY the `Generated Story Components` JSON as your reference.**
2.  For each component, compare the `arc_text` with its corresponding `description`.
3.  Assess if the `arc_text` phrases effectively and accurately distill the key moments from their source `description`.
4.  Provide an overall grade from A (Excellent) to F (Fail) and a justification that analyzes the component-level texts.

**Grading Rubric (Artwork Text Accuracy):**
-   **A (Excellent):** The phrases consistently and poignantly distill the essence of each `description`.
-   **B (Good):** The phrases are largely accurate, but some could be more evocative.
-   **C (Acceptable):** The phrases relate to the events but are sometimes generic or miss the emotional core.
-   **D (Poor):** The phrases are frequently misleading or poorly chosen.
-   **F (Fail):** The phrases do not reflect the content of the `description`.

---
## OUTPUT

Provide your final assessment in the following JSON format ONLY. Do not include any other text or explanation outside of this JSON structure.

```json
{{
  "artwork_text_accuracy": {{
    "grade": "A|B|C|D|F",
    "justification": "Your justification here, based ONLY on the internal consistency between 'arc_text' and 'description'."
  }}
}}
"""
    prompt = PromptTemplate(
        input_variables=["generated_analysis"],
        template=prompt_template)

    config = load_config(config_path=config_path)

    llm = get_llm(llm_provider, llm_model, config, max_tokens=1000)
    
    runnable = prompt | llm

    output = runnable.invoke({"generated_analysis": generated_analysis_str,})

    if hasattr(output, "content"):
        output_text = output.content
    else:
        output_text = output
        
    grade = extract_json(output_text)
    print("--- Artwork Text Accuracy Grade Output ---")
    print(json.dumps(grade, indent=2))
    print("----------------------------------------")
    return grade


if __name__ == 'main':
    try:
        with open('the-great-gatsby_jay-gatsby_8x10.json', 'r') as f:
            gatsby_analysis = json.load(f)
    except FileNotFoundError:
        print("Error: 'the-great-gatsby_jay-gatsby_8x10.json' not found.")
        exit()
    
    CONFIG_PATH = 'config.yaml' 
    LLM_PROVIDER = 'openai'
    LLM_MODEL = 'gpt-4-turbo' 

    grade_text_accuracy(
        config_path=CONFIG_PATH,
        generated_analysis=gatsby_analysis,
        llm_provider=LLM_PROVIDER,
        llm_model=LLM_MODEL
    )