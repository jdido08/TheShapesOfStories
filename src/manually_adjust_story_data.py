from paths import PATHS

# imports 
import os
import time 
import sys
import json
from datetime import datetime

# imports from my code
from story_style import get_story_style, pango_font_exists #move to this sheet
from story_components import get_story_components, grade_story_components, get_distilled_story_components, visualize_distillation, review_story_shape
from story_summary import get_story_summary
from story_shape_category import get_story_symbolic_and_archetype
from story_metadata import get_story_metadata
from story_cover import get_story_cover, manually_set_cover
from langchain_classic.chains import LLMChain

def manually_adjust_story_data(story_data_file_path):
    """
    Re-runs grading, shape categorization, and shape review after manual adjustments
    to story components.
    
    Use this after manually editing the story_components in a story_data.json file.
    
    Args:
        story_data_file_path: Path to the story_data.json file
        
    Returns:
        Updated story_data dict
    """
    print(f"Loading story data from: {story_data_file_path}")
    
    # Load existing story data
    if not os.path.exists(story_data_file_path):
        print(f"❌ Story data file not found: {story_data_file_path}")
        return None
    
    with open(story_data_file_path, 'r') as f:
        story_data = json.load(f)
    
    # Extract needed fields
    story_title = story_data.get("title")
    story_author = story_data.get("author")
    story_protagonist = story_data.get("protagonist")
    story_summary = story_data.get("summary")
    story_components = story_data.get("story_components")
    
    print(f"Story: {story_title} - {story_protagonist}")
    print("Re-running analysis after manual adjustments...")
    
    # 1. Re-grade story components
    story_components_grader_llm_model = "gemini-2.5-pro"
    story_component_grades = grade_story_components(
        config_path=PATHS['config'],
        story_components=story_components,
        canonical_summary=story_summary,
        title=story_title,
        author=story_author,
        protagonist=story_protagonist,
        llm_provider="google",
        llm_model=story_components_grader_llm_model
    )
    print("✅ Story Components Re-Graded")
    print("GRADE: ", story_component_grades['shape_accuracy']['final_grade'])
    
    # 2. Re-calculate shape and archetype
    story_symbolic_rep, story_archetype = get_story_symbolic_and_archetype(story_components)
    print("✅ Story Shape Re-Categorized")
    print("SHAPE: ", story_symbolic_rep)
    
    # 3. Re-review shape
    story_shape_review_llm_model = "claude-sonnet-4-5"
    story_shape_review = review_story_shape(
        config_path=PATHS['config'],
        story_title=story_title,
        author=story_author,
        protagonist=story_protagonist,
        story_summary=story_summary,
        shape=story_symbolic_rep,
        llm_provider="anthropic",
        llm_model=story_shape_review_llm_model
    )
    print(story_shape_review)
    if story_shape_review.get("passes_review") == True:
        print("✅ Story Shape Review Passed")
    else:
        print("❌ Story Shape Review Failed. Further adjustments may be needed.")
    
    # 4. Update story data with new values
    story_data["story_component_grades"] = story_component_grades
    story_data["shape_symbolic_representation"] = story_symbolic_rep
    story_data["shape_archetype"] = story_archetype
    story_data["story_shape_review"] = story_shape_review
    story_data["story_components_adjusted"] = True
    story_data["story_data_adjusted_timestamp"] = datetime.now().isoformat()
    
    # Update LLM models used for re-analysis
    if "llm_models" not in story_data:
        story_data["llm_models"] = {}
    story_data["llm_models"]["story_components_grade"] = story_components_grader_llm_model
    story_data["llm_models"]["story_shape_review"] = story_shape_review_llm_model
    
    # 5. Save updated story data back to file
    with open(story_data_file_path, 'w') as f:
        json.dump(story_data, f, indent=4)
    
    print("✅ Story Data Updated and Saved")
    print("")
    
    return story_data


#TEST
# story_to_adjust = ""
# manually_adjust_story_data(story_to_adjust)