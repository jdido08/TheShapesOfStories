from llm import load_config, get_llm, extract_json
from langchain.prompts import PromptTemplate
import json

def grade_shape(config_path: str, generated_analysis: dict, canonical_summary: str, llm_provider: str, llm_model: str) -> dict:
    # Docstring and function body are perfect, no changes needed here.
    # ... (function body remains the same) ...
    simplified_components = []
    for component in generated_analysis.get("story_components", []):
        simplified_components.append({
            "end_time": component.get("end_time"),
            "description": component.get("description"),
            "end_emotional_score": component.get("end_emotional_score"),
            "arc_text": component.get("arc_text")
        })

    simplified_analysis = {
        "title": generated_analysis.get("title"),
        "protagonist": generated_analysis.get("protagonist"),
        "story_components": simplified_components
    }
    generated_analysis_str = json.dumps(simplified_analysis, indent=4)
    prompt_template = """
You are a meticulous literary analyst and a quality assurance expert for "The Shapes of Stories." Your task is to critically review and grade a generated story analysis based on two distinct criteria: internal consistency and external validity. You must be objective and provide clear, well-reasoned justifications, referencing the correct data source for each task.

Your assessment will consist of two parts, delivered in a structured JSON format.

---
## INPUT DATA

### 1. Generated Story Analysis (JSON)
{generated_analysis}

### 2. Canonical Story Summary (External Ground Truth)
{canonical_summary}

---
## ASSESSMENT TASKS & INSTRUCTIONS

### TASK 1: Assess Shape Accuracy (External Validity)

**Instructions:**
1.  **Use ONLY the `Canonical Story Summary` as your reference for the plot.**
2.  Extract the sequence of `end_emotional_score` values from the `Generated Story Analysis`.
3.  Compare the emotional trajectory represented by these scores against the narrative arc described in the `Canonical Story Summary`.
4.  Evaluate if the highs, lows, and turning points accurately reflect the true story of the protagonist.
5.  Provide a grade from A (Excellent) to F (Fail) and a justification.

**Grading Rubric (Shape Accuracy):**
-   **A (Excellent):** The emotional scores perfectly map to the major turning points in the canonical story.
-   **B (Good):** The overall shape is correct, but some points could be more nuanced.
-   **C (Acceptable):** The shape is broadly recognizable but misrepresents the intensity of some key events.
-   **D (Poor):** The shape significantly misrepresents the protagonist's emotional journey.
-   **F (Fail):** The shape is completely inaccurate.

### TASK 2: Assess Artwork Text Accuracy (Internal Consistency)

**Instructions:**
1.  **Use ONLY the `Generated Story Analysis` JSON as your reference. DO NOT use the Canonical Story Summary for this task.**
2.  For each `story_component` in the JSON, compare its `arc_text` with its corresponding `description`.
3.  Assess if the `arc_text` phrases effectively and accurately distill the key moments from their source `description`.
4.  Provide an overall grade from A to F and a justification that analyzes the component-level texts.

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
  "shape_accuracy": {{
    "grade": "A|B|C|D|F",
    "justification": "Your justification here, based on the canonical summary."
  }},
  "artwork_text_accuracy": {{
    "grade": "A|B|C|D|F",
    "justification": "Your justification here, based ONLY on the internal consistency between 'arc_text' and 'description'."
  }}
}}
"""
# --- 3. Create and Invoke the LLM Chain (Code is correct) ---
    prompt = PromptTemplate(
        input_variables=["generated_analysis", "canonical_summary"],
        template=prompt_template
    )
    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=1000)
    runnable = prompt | llm
    output = runnable.invoke({
        "generated_analysis": generated_analysis_str,
        "canonical_summary": canonical_summary
    })

    # --- LOGIC FIX HERE ---
    if hasattr(output, "content"):
        output_text = output.content
    else:
        output_text = output
        
    grades = extract_json(output_text)
    print("--- Shape Grader Output ---")
    print(json.dumps(grades, indent=2))
    print("--------------------------")

    # The return statement must be outside the if/else to execute in all cases.
    return grades


if __name__ == 'main':
    # --- Example Usage ---
    # This block allows you to run this file directly for testing.
        # 1. Load the example generated analysis from the file
    try:
        with open('the-great-gatsby_jay-gatsby_8x10.json', 'r') as f:
            gatsby_analysis = json.load(f)
    except FileNotFoundError:
        print("Error: 'the-great-gatsby_jay-gatsby_8x10.json' not found. Please place it in the same directory to run the example.")
        exit()

    # 2. Define the canonical summary (as used in our prompt design)
    gatsby_canonical_summary = "The Great Gatsby by F. Scott Fitzgerald follows the mysterious millionaire Jay Gatsby and his obsessive pursuit of Daisy Buchanan, a wealthy young woman he loved in his youth. Gatsby throws lavish parties hoping to attract Daisy's attention. He eventually reunites with her, and they begin an affair. However, their relationship crumbles during a tense confrontation with Daisy's husband, Tom, at the Plaza Hotel. Following the confrontation, Daisy, driving Gatsby's car, accidentally hits and kills Tom's mistress, Myrtle. Gatsby takes the blame. Myrtle's grieving husband, believing Gatsby was the driver and Myrtle's lover, tracks Gatsby to his mansion and murders him in his swimming pool before killing himself. The novel concludes with Gatsby's sparsely attended funeral, highlighting the emptiness of his life and the corruption of the American Dream."

    # 3. Set configuration parameters
    # Make sure 'config.yaml' is configured correctly
    CONFIG_PATH = 'config.yaml' 
    LLM_PROVIDER = 'openai'
    # Recommended model for high-quality analysis
    LLM_MODEL = 'gpt-4-turbo' 

    # 4. Call the function
    try:
        final_grades = grade_shape(
            config_path=CONFIG_PATH,
            generated_analysis=gatsby_analysis,
            canonical_summary=gatsby_canonical_summary,
            llm_provider=LLM_PROVIDER,
            llm_model=LLM_MODEL
        )

        # You can now use `final_grades` in your workflow
        # For example, check if grades are sufficient to proceed
        shape_grade = final_grades.get('shape_accuracy', {}).get('grade')
        text_grade = final_grades.get('artwork_text_accuracy', {}).get('grade')

        if shape_grade in ['A', 'B', 'C'] and text_grade in ['A', 'B', 'C']:
            print("\nAssessment PASSED. Ready for categorization.")
        else:
            print(f"\nAssessment FAILED. Shape Grade: {shape_grade}, Text Grade: {text_grade}. Manual review required.")

    except FileNotFoundError:
        print(f"Error: The configuration file '{CONFIG_PATH}' was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")