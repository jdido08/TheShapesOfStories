from paths import PATHS

# imports 
import os
import time 
import sys
import json
from datetime import datetime

# imports from my code
from story_style import get_story_style, pango_font_exists #move to this sheet
from story_components import get_story_components, grade_story_components
from story_summary import get_story_summary
from story_shape_category import get_story_symbolic_and_archetype
from story_metadata import get_story_metadata

import gi
gi.require_version("Pango", "1.0")
gi.require_version("PangoCairo", "1.0")

from gi.repository import Pango, PangoCairo



#WHAT DOES CRAETE STORY DATA DO???
# INPUTS:
#   - story_type: Literature | Film | Sports | Biographies
#   - story_title: 
#   - story_author (for Literature)
#   - story_protagonist
#   - story_year
#   - story_summary
# LOGIC: Transforms inputs into TSOS Story Data including:
#   - story components --> from story_components.py
#   - validation of story components --> from story_components.py
#   - default style (color + font) --> from story_style.py
#   - story shape
# OUTPUTS: [title]-[protagonist].json
#   - title
#   - author
#   - protagonist
#   - year
#   - summary
#   - story components
#   - grade of story components
#   - default colors + font
#   - story shape category

# This is the helper function that will find our files in Google Drive
def get_google_drive_link(drive_service, file_name, retries=5, delay=10):
    """
    Waits for a file to appear in Google Drive and returns its web link.

    Args:
        drive_service: The authenticated Google Drive service client.
        file_name (str): The name of the file to search for.
        retries (int): The number of times to check for the file.
        delay (int): The number of seconds to wait between checks.

    Returns:
        str: The web link to the file, or an error message if not found.
    """
    print(f"Searching for '{file_name}' in Google Drive...")
    
    for i in range(retries):
        try:
            # Search for the file by its exact name
            response = drive_service.files().list(
                q=f"name='{file_name}' and trashed=false",
                spaces='drive',
                fields='files(id, webViewLink)',
                orderBy='createdTime desc' # Get the most recently created file
            ).execute()
            
            files = response.get('files', [])
            if files:
                file_link = files[0].get('webViewLink')
                print(f"Success! Found file link: {file_link}")
                return file_link
            else:
                print(f"File not found yet. Retrying in {delay} seconds... (Attempt {i+1}/{retries})")
                time.sleep(delay)

        except Exception as e:
            print(f"An error occurred while searching for the file: {e}")
            return "Error finding file"
            
    print(f"File '{file_name}' could not be found in Google Drive after several retries.")
    return "File not found"

# ==============================================================================
#           UNIFIED PATH CONFIGURATION (for Local & Colab)
# ==============================================================================
import os
import sys

# # This dictionary will hold all our configured paths
# PATHS = {}

# local_drive_path = os.path.expanduser('~/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive')
# if not os.path.exists(local_drive_path): # Fallback for older Google Drive versions
#     local_drive_path = '/Volumes/GoogleDrive/My Drive'

# BASE_DIR = local_drive_path

# # --- Define all other paths relative to the base directory ---
# PATHS['src'] = os.path.join(BASE_DIR, 'src')
# PATHS['summaries'] = os.path.join(BASE_DIR, 'summaries')
# PATHS['story_data'] = os.path.join(BASE_DIR, 'story_data')
# PATHS['product_data'] = os.path.join(BASE_DIR, 'product_data')
# PATHS['product_designs'] = os.path.join(BASE_DIR, 'product_designs')
# PATHS['shapes_output'] = os.path.join(BASE_DIR, 'story_shapes')
# PATHS['supporting_designs'] = os.path.join(BASE_DIR, 'supporting_designs')
# PATHS['product_mockups'] = os.path.join(BASE_DIR, 'product_mockups')
# PATHS['config'] = os.path.join(BASE_DIR, 'config.yaml')

# # --- Automatically create output directories if they don't exist ---
# os.makedirs(PATHS['story_data'], exist_ok=True)
# os.makedirs(PATHS['shapes_output'], exist_ok=True)

# # --- Add the 'src' directory to the system path ---
# # This allows your scripts to import from each other using "from llm import ..."
# sys.path.append(PATHS['src'])

# # --- Verify that the base directory exists ---
# if not os.path.exists(BASE_DIR):
#     raise FileNotFoundError(f"The base directory was not found at: {BASE_DIR}\n"
#                             "Please check your path configuration for the current environment.")

# print(f"\nProject Base Directory: {BASE_DIR}")
# print("All paths configured successfully.")


def create_story_data(story_type, story_title, story_author,story_protagonist, story_year, story_summary_path, build_story_summary=True):
    print("Story: ", story_title, " - ", story_protagonist)

    # create story data file name --> [story_title]-[story_protagonist].json
    story_data_file_name = story_title.lower().replace(' ', '-') + "-" + story_protagonist.lower().replace(' ', '-')
    story_data_file_name = story_data_file_name.replace("’", "'")   # Normalize the path to replace curly apostrophes with straight ones
    story_data_file_name = story_data_file_name.replace(",", "")    # Normalize the path to replace commas

    # check if story data already exits
    story_data_file_path = os.path.join(PATHS['story_data'], story_data_file_name + ".json")     # Use the configured path
    
    # don't proceed forward if story data exists --> ask user to delete it first
    # this will prevent accidential rewrites of story data
    if os.path.exists(story_data_file_path):
        print("❌ Story Data Already Exists. Please Delete Existing Story Data First!. Skipping.")
        return 
    

    # get story summary from story summary path 
    #story_summary = get_story_summary(story_summary_path)
    if build_story_summary == True:
        story_summary_llm_model = "gemini-2.5-pro"
        story_summary = get_story_summary(
            story_title=story_title, 
            story_author=story_author, 
            story_protagonist=story_protagonist, 
            story_summary_path=story_summary_path, 
            config_path=PATHS['config'],
            llm_provider="google", 
            llm_model=story_summary_llm_model)
        if story_summary is not None:
            print("✅ Story Summary Created")
    else:
        with open(story_summary_path, 'r') as f:
            story_summary_data = json.load(f)
        story_summary = story_summary_data.get("summary")
        print("✅ Story Summary Loaded")



    # get story components --> don't use google you often get blocked
    story_components_llm_model = "gemini-2.5-pro"
    story_components = get_story_components(
        config_path=PATHS['config'],
        story_title=story_title,
        story_summary = story_summary,
        author=story_author,
        year=story_year,
        protagonist=story_protagonist,
        llm_provider = "google", #"google", #"openai",#, #"openai",, #"anthropic", #google", 
        llm_model = story_components_llm_model#"gemini-2.5-pro-preview-06-05", #o3-mini-2025-01-31", #"o4-mini-2025-04-16" #"gemini-2.5-pro-preview-05-06" #"o3-2025-04-16" #"gemini-2.5-pro-preview-05-06"#o3-2025-04-16"#"gemini-2.5-pro-preview-05-06" #"claude-3-5-sonnet-latest" #"gemini-2.5-pro-preview-03-25"
    )
    print("✅ Story Components Created")

    #grade story components
    story_components_grader_llm_model = "gemini-2.5-pro"
    story_component_grades = grade_story_components(
        config_path = PATHS['config'], 
        story_components=story_components, 
        canonical_summary=story_summary, 
        title=story_title, 
        author=story_author, 
        protagonist=story_protagonist, 
        llm_provider = "google", #"google", #"openai",#, #"openai",, #"anthropic", #google", 
        llm_model = story_components_grader_llm_model#"gemini-2.5-pro-preview-06-05", #o3-mini-2025-01-31", #"o4-mini-2025-04-16" #"gemini-2.5-pro-preview-05-06" #"o3-2025-04-16" #"gemini-2.5-pro-preview-05-06"#o3-2025-04-16"#"gemini-2.5-pro-preview-05-06" #"claude-3-5-sonnet-latest" #"gemini-2.5-pro-preview-03-25"
    )
    print("✅ Story Components Graded")

    
    # get category of shape
    story_symbolic_rep,  story_archetype = get_story_symbolic_and_archetype(story_components)
    print("✅ Story Shape Category")
    
    # get stort style
    story_style_llm_model = "claude-sonnet-4-5"
    story_style = get_story_style(
        config_path = PATHS['config'],
        story_title = story_title, 
        author = story_author,
        protagonist = story_protagonist, 
        llm_provider = "anthropic", #"google", #"openai",#, #"openai",, #"anthropic", #google", 
        llm_model = story_style_llm_model#"gemini-2.5-pro-preview-06-05", #o3-mini-2025-01-31", #"o4-mini-2025-04-16" #"gemini-2.5-pro-preview-05-06" #"o3-2025-04-16" #"gemini-2.5-pro-preview-05-06"#o3-2025-04-16"#"gemini-2.5-pro-preview-05-06" #"claude-3-5-sonnet-latest" #"gemini-2.5-pro-preview-03-25"
    )
    story_style = json.loads(story_style)
    design_rationale        = story_style.get('design_rationale')
    design_background_color = story_style.get('background_color')
    design_font_color       = story_style.get('font_color')
    design_border_color     = story_style.get('border_color')
    design_font             = story_style.get('font')
    print("✅ Story Style")
    
    #check if font supported in local environment
    if design_font and not pango_font_exists(design_font):
        raise ValueError(f"'{design_font}' not found on this system.")
    

    # save story data back as json 
    story_data = {
        "story_slug":story_data_file_name,
        "title": story_title,
        "author": story_author,
        "protagonist": story_protagonist, 
        "year": story_year,
        "story_type": story_type,
        "shape_symbolic_representation": story_symbolic_rep,
        "shape_archetype": story_archetype,
        "story_components": story_components,
        "default_style": {
            "background_color_hex": design_background_color,
            "font_color_hex": design_font_color,
            "border_color_hex": design_border_color,
            "font": design_font,
            "design_rationale":design_rationale
        },
        "summary": story_summary,
        "story_summary_sources_path":story_summary_path,

        "story_component_grades":story_component_grades,
        "llm_models": {
            "story_summary": story_summary_llm_model,
            "story_components": story_components_llm_model,
            "story_components_grade": story_components_grader_llm_model,
            "story_default_style": story_style_llm_model
        },
        "story_manual_colletion":[],
        "story_data_create_timestamp":datetime.now().isoformat()
    }

    # Write story data to JSON
    with open(story_data_file_path, 'w') as f:
        json.dump(story_data, f, indent=4)
    
    #wait a few seconds 
    time.sleep(3)
    print("✅ Story Data Saved")


    #get story metadata
    story_metadata_llm_provider = "anthropic"
    story_metadata_llm_model = "claude-sonnet-4-5"
    get_story_metadata(
        story_json_path=story_data_file_path,
        use_llm="on",
        config_path=PATHS['config'],
        llm_provider=story_metadata_llm_provider,
        llm_model=story_metadata_llm_model
    )
    print("✅ Story MetaData")
    print("")
    return story_data_file_path

    

    




# Examle Call 		
# create_story_data(story_type="Literature", 
#                   story_title="The Stranger", 
#                   story_author="Albert Camus",
#                   story_protagonist="Meursault", 
#                   story_year="1942", 
#                   story_summary_path="/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/summaries/the_stranger_composite_data.json")

