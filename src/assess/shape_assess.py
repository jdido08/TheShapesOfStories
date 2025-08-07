# shape_assess.py
#This is the main orchestrator file. It imports the functions from the other two files and runs the complete, end-to-end assessment workflow.


import json
import os
from shape_grader import grade_shape
from shape_categorizer import categorize_shape

def assess_story_shape(generated_analysis_path: str, canonical_summary: str, config_path: str = 'config.yaml'):
    """
    Orchestrates the full quality assessment workflow for a story shape.

    This function performs a two-step process:
    1.  Calls the 'grade_shape' function to get quality grades.
    2.  If grades are sufficient, it calls the 'categorize_shape' function.
    3.  Returns a final assessment object with all results.

    Args:
        generated_analysis_path (str): The file path to the generated story JSON.
        canonical_summary (str): An objective, external summary of the story.
        config_path (str, optional): Path to the LLM configuration file. Defaults to 'config.yaml'.

    Returns:
        dict: A comprehensive dictionary containing the grades, justifications,
              and category (if assessment passed).
    """
    print(f"--- Starting Assessment for {generated_analysis_path} ---")

    # --- Load Data ---
    if not os.path.exists(generated_analysis_path):
        print(f"Error: Analysis file not found at {generated_analysis_path}")
        return {
            "status": "error",
            "message": "Analysis file not found."
        }
    
    with open(generated_analysis_path, 'r') as f:
        generated_analysis = json.load(f)

    # --- Step 1: Grade the Shape and Text ---
    # We use a powerful model for this analytical step.
    grader_llm_provider = 'openai'
    grader_llm_model = 'gpt-4-turbo'
    
    try:
        grades = grade_shape(
            config_path=config_path,
            generated_analysis=generated_analysis,
            canonical_summary=canonical_summary,
            llm_provider=grader_llm_provider,
            llm_model=grader_llm_model
        )
    except Exception as e:
        print(f"An error occurred during the grading step: {e}")
        return {"status": "error", "message": f"Grading failed: {e}"}

    # --- Step 2: The "Gatekeeper" - Check Grades ---
    shape_grade = grades.get('shape_accuracy', {}).get('grade')
    text_grade = grades.get('artwork_text_accuracy', {}).get('grade')

    final_assessment = {
        "source_file": generated_analysis_path,
        "grades": grades,
        "assessment_status": "failed",
        "category_info": None
    }

    if shape_grade not in ['A', 'B', 'C'] or text_grade not in ['A', 'B', 'C']:
        print(f"\nAssessment FAILED. Shape Grade: {shape_grade}, Text Grade: {text_grade}. Halting process.")
        final_assessment["assessment_status"] = f"failed_quality_check (Shape: {shape_grade}, Text: {text_grade})"
        return final_assessment

    print("\nAssessment PASSED quality check. Proceeding to categorization.")
    final_assessment["assessment_status"] = "passed"

    # --- Step 3: Categorize the Shape ---
    # We use a cheaper, faster model for this rule-based step.
    categorizer_llm_provider = 'openai'
    categorizer_llm_model = 'gpt-3.5-turbo'

    emotional_scores = [comp['end_emotional_score'] for comp in generated_analysis["story_components"]]
    
    try:
        category_info = categorize_shape(
            config_path=config_path,
            emotional_scores=emotional_scores,
            llm_provider=categorizer_llm_provider,
            llm_model=categorizer_llm_model
        )
        final_assessment["category_info"] = category_info
    except Exception as e:
        print(f"An error occurred during the categorization step: {e}")
        final_assessment["assessment_status"] = "passed_grading_but_categorization_failed"
        final_assessment["category_info"] = {"error": str(e)}

    return final_assessment

if __name__ == '__main__':
    # Define the inputs for the assessment
    ANALYSIS_FILE = 'the-great-gatsby_jay-gatsby_8x10.json'
    CANONICAL_SUMMARY = "The Great Gatsby by F. Scott Fitzgerald follows the mysterious millionaire Jay Gatsby and his obsessive pursuit of Daisy Buchanan, a wealthy young woman he loved in his youth. Gatsby throws lavish parties hoping to attract Daisy's attention. He eventually reunites with her, and they begin an affair. However, their relationship crumbles during a tense confrontation with Daisy's husband, Tom, at the Plaza Hotel. Following the confrontation, Daisy, driving Gatsby's car, accidentally hits and kills Tom's mistress, Myrtle. Gatsby takes the blame. Myrtle's grieving husband, believing Gatsby was the driver and Myrtle's lover, tracks Gatsby to his mansion and murders him in his swimming pool before killing himself. The novel concludes with Gatsby's sparsely attended funeral, highlighting the emptiness of his life and the corruption of the American Dream."
    CONFIG_FILE = 'config.yaml'

    # Run the full assessment
    full_result = assess_story_shape(
        generated_analysis_path=ANALYSIS_FILE,
        canonical_summary=CANONICAL_SUMMARY,
        config_path=CONFIG_FILE
    )

    print("\n--- FINAL ASSESSMENT RESULT ---")
    print(json.dumps(full_result, indent=2))
    print("-------------------------------")