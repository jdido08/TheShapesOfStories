# grade_shape_accuracy.py

from llm import load_config, get_llm, extract_json
from langchain.prompts import PromptTemplate
import json
import os
from datetime import datetime


def grade_shape_accuracy(config_path: str, generated_analysis: dict, canonical_summary: str, llm_provider: str, llm_model: str) -> dict:
  """
  Grades the accuracy of a story's emotional shape using a two-phase analysis.

  Phase 1 (Bottom-Up): Verifies that each emotional transition is factually justified.
  Phase 2 (Top-Down): Assesses the holistic accuracy of the entire emotional arc,
  checking for correct proportions, pacing, and identification of key turning points.

  Args:
      config_path (str): Path to the LLM configuration file.
      generated_analysis (dict): The generated story JSON.
      canonical_summary (str): An objective, external summary of the story.
      llm_provider (str): The LLM provider to use.
      llm_model (str): The specific LLM model to use (e.g., 'gpt-4-turbo').

  Returns:
      dict: A detailed dictionary with both component-level and holistic assessments.
  """
  
  # --- 1. Prepare Inputs for the Prompt ---
  simplified_components = []
  # Start with the initial state as the first component for the prompt
  initial_component = generated_analysis.get("story_components", [{}])[0]
  simplified_components.append({
      "end_time": initial_component.get("end_time"),
      "description": "Initial State",
      "end_emotional_score": initial_component.get("end_emotional_score")
  })
  for component in generated_analysis.get("story_components", []):
      if component.get("end_time") > 0:
          simplified_components.append({
              "end_time": component.get("end_time"),
              "description": component.get("description"),
              "end_emotional_score": component.get("end_emotional_score")
          })
          
  analysis_to_grade = {
      "title": generated_analysis.get("title"),
      "protagonist": generated_analysis.get("protagonist"),
      "story_components_with_scores": simplified_components
  }
  generated_analysis_str = json.dumps(analysis_to_grade, indent=4)

# FIX: Extract new variables to pass to the prompt
  title = generated_analysis.get("title", "this story")
  author = generated_analysis.get("author", "the author")
  protagonist = generated_analysis.get("protagonist", "the protagonist")


  # --- 2. Define the Two-Phase Prompt ---
  prompt_template = """
You are an expert literary scholar specializing in narrative theory and the quantitative analysis of story structures. You are trained to evaluate character arcs with academic rigor, objectivity, and precision. 

Your task is to perform a rigorous two-phase quality assessment of a story's emotional shape.


---
## INPUT DATA

### 1. Generated Story Analysis
This JSON contains the proposed emotional scores for {protagonist} from {author}'s {title} and the text descriptions for each story segment. 
Emotional scores range from euphoric (+10) to depressed (-10), based on {protagonist}'s direct experiences and reactions to events in each story segment.
{generated_analysis}

### 2. Canonical Story Summary (External Ground Truth)
This text is the source of truth for the story's events.
"{canonical_summary}"

---
## FRAMEWORK FOR JUDGMENT (Your Analytical Rubric)

You must apply the following principles when assessing the emotional scores:
1.  **Anchoring:** Scores must be anchored to the protagonist's emotional stakes. +10 represents ultimate triumph/euphoria; -10 represents ultimate despair/tragedy (e.g., death, total failure).
2.  **Proportionality:** The *magnitude* of a score change must be proportional to the *magnitude* of the causal event. A minor setback should not cause a 10-point drop.
3.  **Narrative Weight:** The story's most pivotal moment (the climax or point of no return) should be clearly identifiable in the trajectory, often marked by the largest emotional shift.

---
## ASSESSMENT & INSTRUCTIONS

### Phase 1: Bottom-Up Component Validation
For each emotional transition, determine if the event in the `description` factually justifies the change in `end_emotional_score` according to the `Canonical Story Summary`.

### Phase 2: Top-Down Holistic Review
After completing Phase 1, evaluate the entire emotional journey using the `FRAMEWORK FOR JUDGMENT`.
-   Is the shape **proportional** and well-paced?
-   Are the scores correctly **anchored** to the story's stakes?
-   Does the shape give appropriate **narrative weight** to the climax?

### Final Grade
Your `final_grade` must be the more critical of the two assessments. A story can have factually correct components but a holistically incorrect shape.

---
## OUTPUT

Provide your complete two-phase assessment in the following JSON format ONLY.

```json
{{
"shape_accuracy": {{
  "component_assessments": [
    {{
      "end_time": 40, 
      "emotional_transition": "1 -> 8",
      "is_justified": true,
      "reasoning": "The reunion with Daisy after years of obsession justifies a significant rise to euphoria."
    }},
    {{
      "end_time": 55,
      "emotional_transition": "8 -> 4",
      "is_justified": true,
      "reasoning": "Daisy's negative reaction to the party correctly tempers Gatsby's euphoria, justifying a moderate fall."
    }}
  ],
  "holistic_assessment": {{
      "holistic_grade": "A|B|C|D|F",
      "holistic_justification": "The overall shape brilliantly captures the Icarus-like rise fueled by hope and the subsequent, catastrophic collapse into tragedy. The proportions feel correct, with the final fall being the most significant move."
  }},
  "final_grade": "A|B|C|D|F",
  "final_justification": "The final grade is A because both the individual components are logically sound and the overall shape accurately reflects the tragic spirit and proportions of the novel."
}}
}}
"""

  prompt = PromptTemplate(
      input_variables=["generated_analysis", "canonical_summary", "title", "author", "protagonist"],
      template=prompt_template
  )
  config = load_config(config_path=config_path)
  llm = get_llm(llm_provider, llm_model, config, max_tokens=4000) # Increased tokens for the more detailed analysis
  runnable = prompt | llm
  output = runnable.invoke({
        "generated_analysis": generated_analysis_str,
        "canonical_summary": canonical_summary,
        "title": title,
        "author": author,
        "protagonist": protagonist
    })

  if hasattr(output, "content"):
      output_text = output.content
  else:
      output_text = output

  ## --- FIXES ARE IN THIS FINAL SECTION --- ##

  extracted_text = extract_json(output_text)
    
  try:
      # The `extracted_text` is a string; we load it into our dictionary.
      grades_dict = json.loads(extracted_text)
  except (json.JSONDecodeError, TypeError) as e:
      print(f"Error parsing JSON from LLM output: {e}")
      print(f"Raw extracted text was: {extracted_text}")
      # Return a dictionary with an error state to prevent crashes downstream
      return {"error": "Failed to parse LLM response as JSON."}
      
  # 1. REMOVED the redundant line: `grade = extract_json(output_text)`
  
  # 2. UPDATED to print the dictionary, not the string.
  print("--- Shape Accuracy Grade Output (Parsed) ---")
  print(json.dumps(grades_dict, indent=2))
  print("------------------------------------------")
  
  # 3. UPDATED to return the dictionary `grades_dict`.
  return grades_dict


# shape_assess.py



def assess_story_shape(generated_analysis_path: str, canonical_summary: str, config_path: str = 'config.yaml'):
    """
    Orchestrates a focused quality assessment for a story's shape and updates the
    source JSON file with the results.

    This function performs a single, focused task:
    1.  Calls the `grade_shape_accuracy` function to get a detailed quality grade.
    2.  Adds a `shape_quality_assessment` object to the loaded JSON data.
    3.  Saves the updated data with the grading results back to the original file.

    Args:
        generated_analysis_path (str): The file path to the story data JSON.
        canonical_summary (str): An objective, external summary of the story.
        config_path (str, optional): Path to the LLM configuration file. Defaults to 'config.yaml'.
    """
    print(f"--- Starting Shape Accuracy Assessment for {generated_analysis_path} ---")

    # --- Step 1: Load the story data ---
    if not os.path.exists(generated_analysis_path):
        print(f"Error: Analysis file not found at {generated_analysis_path}")
        return
    
    with open(generated_analysis_path, 'r') as f:
        generated_analysis = json.load(f)

    # --- Step 2: Grade the Shape Accuracy ---
    # We use a powerful model for this analytical step.
    grader_llm_provider = 'anthropic'#'google'
    grader_llm_model = 'claude-sonnet-4-20250514'#'gemini-2.5-pro'

    if not canonical_summary:
      canonical_summary = generated_analysis.get('summary', '')
    
    try:
        # The function returns the entire 'shape_accuracy' object
        shape_grade_result = grade_shape_accuracy(
            config_path=config_path,
            generated_analysis=generated_analysis,
            canonical_summary=canonical_summary,
            llm_provider=grader_llm_provider,
            llm_model=grader_llm_model
        )
    except Exception as e:
        print(f"An error occurred during the grading step: {e}")
        # Even if it fails, let's log the failure to the file
        generated_analysis['shape_quality_assessment'] = {
            "status": "grading_error",
            "error_message": str(e),
            "assessment_timestamp": datetime.now().isoformat()
        }
        with open(generated_analysis_path, 'w') as f:
            json.dump(generated_analysis, f, indent=4)
        return

    # --- Step 3: Prepare and save the results ---
    
    # Create or update the shape_quality_assessment key
    generated_analysis['shape_quality_assessment'] = {
        "shape_accuracy_assessment": shape_grade_result.get('shape_accuracy'),
        "assessment_timestamp": datetime.now().isoformat(),
        "grading_model": grader_llm_model
    }

    # Determine the final status based on the grade
    final_grade = shape_grade_result.get('shape_accuracy', {}).get('final_grade')
    if final_grade in ['A', 'B', 'C']:
        generated_analysis['shape_quality_assessment']['status'] = "passed_shape_check"
        print(f"\nAssessment PASSED. Shape Grade: {final_grade}")
    else:
        generated_analysis['shape_quality_assessment']['status'] = f"failed_shape_check (Grade: {final_grade})"
        print(f"\nAssessment FAILED. Shape Grade: {final_grade}")

    # Write the enriched data back to the original file
    with open(generated_analysis_path, 'w') as f:
        json.dump(generated_analysis, f, indent=4)
        
    print(f"Successfully updated {generated_analysis_path} with shape accuracy assessment.")

if __name__ == '__main__':
    # Define the inputs for the assessment
    ANALYSIS_FILE = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/for-whom-the-bell-tolls_robert-jordan_8x10.json"
    CANONICAL_SUMMARY = ""
    CONFIG_FILE = 'config.yaml'

    # Run the focused assessment
    assess_story_shape(
        generated_analysis_path=ANALYSIS_FILE,
        canonical_summary=CANONICAL_SUMMARY,
        config_path=CONFIG_FILE
    )