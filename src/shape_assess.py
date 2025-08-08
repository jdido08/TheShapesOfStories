# shape_assess.py

import json
import os
# Updated imports for the new, specialized grader functions
from grade_shape_accuracy import grade_shape_accuracy
from grade_text_accuracy import grade_text_accuracy
from shape_categorizer import categorize_shape

def assess_story_shape(generated_analysis_path: str, canonical_summary: str, config_path: str = 'config.yaml'):
    """
    Orchestrates the full quality assessment workflow for a story shape.

    This function performs a three-step process:
    1.  Calls `grade_shape_accuracy` to assess the emotional shape.
    2.  Calls `grade_text_accuracy` to assess the artwork text.
    3.  If both grades are sufficient, it calls `categorize_shape`.
    4.  Returns a final assessment object with all results.

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
        return {"status": "error", "message": "Analysis file not found."}
    
    with open(generated_analysis_path, 'r') as f:
        generated_analysis = json.load(f)

    # --- Step 1A: Grade the Shape Accuracy ---
    # We use a powerful model for these analytical steps.
    grader_llm_provider = 'google'
    grader_llm_model = 'gemini-2.5-pro'
    
    try:
        print("\n--> Assessing Shape Accuracy (External Validity)...")
        shape_grade_result = grade_shape_accuracy(
            config_path=config_path,
            generated_analysis=generated_analysis,
            canonical_summary=canonical_summary,
            llm_provider=grader_llm_provider,
            llm_model=grader_llm_model
        )
    except Exception as e:
        print(f"An error occurred during the shape grading step: {e}")
        return {"status": "error", "message": f"Shape grading failed: {e}"}

    # # --- Step 1B: Grade the Text Accuracy ---
    # try:
    #     print("\n--> Assessing Text Accuracy (Internal Consistency)...")
    #     text_grade_result = grade_text_accuracy(
    #         config_path=config_path,
    #         generated_analysis=generated_analysis,
    #         llm_provider=grader_llm_provider,
    #         llm_model=grader_llm_model
    #     )
    # except Exception as e:
    #     print(f"An error occurred during the text grading step: {e}")
    #     return {"status": "error", "message": f"Text grading failed: {e}"}

    # # --- Step 2: The "Gatekeeper" - Combine and Check Grades ---
    
    # # Merge the results from the two grading steps
    # all_grades = {**shape_grade_result, **text_grade_result}
    
    # shape_grade = all_grades.get('shape_accuracy', {}).get('grade')
    # text_grade = all_grades.get('artwork_text_accuracy', {}).get('grade')

    # final_assessment = {
    #     "source_file": generated_analysis_path,
    #     "grades": all_grades,
    #     "assessment_status": "failed",
    #     "category_info": None
    # }

    # if shape_grade not in ['A', 'B', 'C'] or text_grade not in ['A', 'B', 'C']:
    #     print(f"\nAssessment FAILED. Shape Grade: {shape_grade}, Text Grade: {text_grade}. Halting process.")
    #     final_assessment["assessment_status"] = f"failed_quality_check (Shape: {shape_grade}, Text: {text_grade})"
    #     return final_assessment

    # print("\nAssessment PASSED quality check. Proceeding to categorization.")
    # final_assessment["assessment_status"] = "passed"

    # # --- Step 3: Categorize the Shape ---
    # # We use a cheaper, faster model for this rule-based step.
    # categorizer_llm_provider = 'google'
    # categorizer_llm_model = 'gemini-2.5-pro'

    # emotional_scores = [comp['end_emotional_score'] for comp in generated_analysis["story_components"]]
    
    # try:
    #     print("\n--> Categorizing Shape...")
    #     category_info = categorize_shape(
    #         config_path=config_path,
    #         emotional_scores=emotional_scores,
    #         llm_provider=categorizer_llm_provider,
    #         llm_model=categorizer_llm_model
    #     )
    #     final_assessment["category_info"] = category_info
    # except Exception as e:
    #     print(f"An error occurred during the categorization step: {e}")
    #     final_assessment["assessment_status"] = "passed_grading_but_categorization_failed"
    #     final_assessment["category_info"] = {"error": str(e)}

    # return final_assessment

if __name__ == '__main__':
    # Define the inputs for the assessment
    ANALYSIS_FILE = '/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-great-gatsby_jay-gatsby_8x10.json'
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