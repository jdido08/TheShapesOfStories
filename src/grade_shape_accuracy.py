# grade_shape_accuracy.py

from llm import load_config, get_llm, extract_json
from langchain.prompts import PromptTemplate
import json

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
      "emotional_transition": "1 -> 8",
      "is_justified": true,
      "reasoning": "The reunion with Daisy after years of obsession justifies a significant rise to euphoria."
    }},
    {{
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
      input_variables=["generated_analysis", "canonical_summary"],
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
      
  grade = extract_json(output_text)
  print("--- Shape Accuracy Grade Output (Two-Phase) ---")
  print(json.dumps(grade, indent=2))
  print("---------------------------------------------")
  return grade