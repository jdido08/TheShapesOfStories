from google.oauth2.service_account import Credentials
import gspread
import yaml

#imports
from story_style import get_story_style #move to this sheet
from story_components import get_story_components, grade_story_components
from story_summary import get_story_summary
from story_shape_category import get_story_symbolic_and_archetype
from datetime import datetime


from story_shape import create_shape
import json 
import os
import re
import time 
import platform
from PIL import ImageFont
from googleapiclient.discovery import build
import webcolors



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

from matplotlib import font_manager
import sys

from llm import load_config, get_llm, extract_json
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
import yaml
import tiktoken
import json 
import os 


def get_font_path(font_name):
    """
    Finds the full file path for a given font name using matplotlib's font manager.

    Args:
        font_name (str): The name of the font to find (e.g., "Merriweather").

    Returns:
        str: The full file path to the font. Exits script if font is not found.
    """
    try:
        # findfont will search your system and return the best match.
        # The FontProperties object is needed to properly query the font.
        font_prop = font_manager.FontProperties(family=font_name)
        return font_manager.findfont(font_prop)
    except ValueError:
        # This error is raised if findfont can't find any matching font.
        print(f"--- FONT FINDER ERROR ---", file=sys.stderr)
        print(f"The font '{font_name}' could not be found by the font manager.", file=sys.stderr)
        print("Please ensure it is properly installed and its cache is updated.", file=sys.stderr)
        sys.exit(1)


def pango_font_exists(font_name):
    from gi.repository import Pango, PangoCairo
    """
    Checks whether the given font is available using Pango.
    Returns True if the font is found, False otherwise.
    """
    if not font_name:
        return True  # nothing to check if font_name is empty

    # Get the default font map from PangoCairo.
    font_map = PangoCairo.FontMap.get_default()
    families = font_map.list_families()

    # Iterate through the font families and see if any name matches (case-insensitive).
    for family in families:
        if font_name.lower() in family.get_name().lower():
            return True

    return False


from googleapiclient.discovery import build
import time

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

# This dictionary will hold all our configured paths
PATHS = {}

# Example for macOS:
local_drive_path = os.path.expanduser('~/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive')
if not os.path.exists(local_drive_path): # Fallback for older Google Drive versions
    local_drive_path = '/Volumes/GoogleDrive/My Drive'

# Example for Windows:
# local_drive_path = 'G:\\My Drive' # Use a raw string or double backslashes

#BASE_DIR = os.path.join(local_drive_path, 'Projects/TheShapesOfStories')
BASE_DIR = local_drive_path
print(BASE_DIR)

# --- Define all other paths relative to the base directory ---
PATHS['src'] = os.path.join(BASE_DIR, 'src')
PATHS['summaries'] = os.path.join(BASE_DIR, 'data', 'summaries')
PATHS['story_data'] = os.path.join(BASE_DIR, 'data', 'story_data')
PATHS['product_data'] = os.path.join(BASE_DIR, 'data', 'product_data')
PATHS['product_designs'] = os.path.join(BASE_DIR, 'data', 'product_designs')
PATHS['shapes_output'] = os.path.join(BASE_DIR, 'data', 'story_shapes')
PATHS['config'] = os.path.join(BASE_DIR, 'config.yaml')

# --- Automatically create output directories if they don't exist ---
os.makedirs(PATHS['story_data'], exist_ok=True)
os.makedirs(PATHS['shapes_output'], exist_ok=True)

# --- Add the 'src' directory to the system path ---
# This allows your scripts to import from each other using "from llm import ..."
sys.path.append(PATHS['src'])

# --- Verify that the base directory exists ---
if not os.path.exists(BASE_DIR):
    raise FileNotFoundError(f"The base directory was not found at: {BASE_DIR}\n"
                            "Please check your path configuration for the current environment.")

print(f"\nProject Base Directory: {BASE_DIR}")
print("All paths configured successfully.")


def load_credentials_from_yaml(file_path):
    with open(file_path, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config["google_sheets"]

# Use the configured path from the PATHS dictionary
creds_data = load_credentials_from_yaml(PATHS['config'])

# Define the correct scope
# SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
]

# Create credentials with the correct scope
credentials = Credentials.from_service_account_info(creds_data, scopes=SCOPES)

# Authorize and create a client
client = gspread.authorize(credentials)

# NOW, USE THE SAME CREDENTIALS TO BUILD THE GOOGLE DRIVE CLIENT
try:
    drive_service = build('drive', 'v3', credentials=credentials)
    print("Google Drive service client created successfully.")
except Exception as e:
    print(f"An error occurred while building the Drive service: {e}")
    exit()


# Open the Google Sheet by its ID
#link https://docs.google.com/spreadsheets/d/1T0ThSHKK_sMIKTdwC14WZoWFNFD3dU7xIheQ5AF9NLU/edit?usp=sharing
# sheet_id = "1C0CytarUcbUrRpqi5RK7MJUOb2DBR_bjQ_IeqcCi-Yw"
# spreadsheet = client.open_by_key(sheet_id)
# worksheet = spreadsheet.sheet1 # Access the first worksheet


# Get all rows from the sheet
# rows = worksheet.get_all_records()

# #loop through all rows but really should just be first row
# for row in rows:

#     #get input parameters from sheet
#     story_type          = row.get('story_type')
#     story_title	        = row.get('story_title')    
#     story_author	    = row.get('story_author')
#     story_protagonist	= row.get('story_protagonist')
#     story_year	        = row.get('story_year')
#     story_summary_path  = row.get('story_summary_path')




def create_story_data(story_type, story_title, story_author,story_protagonist, story_year, story_summary_path):

    # create story data file name --> [story_title]-[story_protagonist].json
    story_data_file_name = story_title.lower().replace(' ', '_') + "-" + story_protagonist.lower().replace(' ', '_')
    story_data_file_name = story_data_file_name.replace("’", "'")   # Normalize the path to replace curly apostrophes with straight ones
    story_data_file_name = story_data_file_name.replace(",", "")    # Normalize the path to replace commas

    # check if story data already exits
    story_data_file_path = os.path.join(PATHS['story_data'], story_data_file_name + ".json")     # Use the configured path
    
    # don't proceed forward if story data exists --> ask user to delete it first
    # this will prevent accidential rewrites of story data
    if os.path.exists(story_data_file_path):
        raise ValueError("Story Data Already Exists. Please Delete Existing Story Data First!")
    

    # get story summary from story summary path 
    story_summary = get_story_summary(story_summary_path)

    # get story components --> don't use google you often get blocked
    story_components_llm_model = "claude-3-5-sonnet-latest"
    story_components = get_story_components(
        config_path=PATHS['config'],
        story_title=story_title,
        story_summary = story_summary,
        author=story_author,
        year=story_year,
        protagonist=story_protagonist,
        llm_provider = "anthropic", #"google", #"openai",#, #"openai",, #"anthropic", #google", 
        llm_model = story_components_llm_model#"gemini-2.5-pro-preview-06-05", #o3-mini-2025-01-31", #"o4-mini-2025-04-16" #"gemini-2.5-pro-preview-05-06" #"o3-2025-04-16" #"gemini-2.5-pro-preview-05-06"#o3-2025-04-16"#"gemini-2.5-pro-preview-05-06" #"claude-3-5-sonnet-latest" #"gemini-2.5-pro-preview-03-25"
    )

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

    
    # get category of shape
    story_symbolic_rep,  story_archetype = get_story_symbolic_and_archetype(story_components)
    
    # get stort style
    story_style_llm_model = "claude-3-5-sonnet-latest"
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
    
    #check if font supported in local environment
    if design_font and not pango_font_exists(design_font):
        raise ValueError(f"'{design_font}' not found on this system.")


    story_data = {
        "title": story_title,
        "author": story_author,
        "protagonist": story_protagonist, 
        "year": story_year,
        "shape_symbolic_representation": story_symbolic_rep,
        "shape_archetype": story_archetype,
        "story_components": story_components,
        "default_style": {
            "background_color": design_background_color,
            "font_color": design_font_color,
            "border_color": design_border_color,
            "font": design_font,
            "design_rationale":design_rationale
        },
        "story_type": story_type,
        "summary": story_summary,
        "story_component_grades":story_component_grades,
        "llm_models": {
            "story_components": story_components_llm_model,
            "story_components_grade": story_components_grader_llm_model,
            "story_default_style": story_style_llm_model
        },
        "story_data_create_timestamp":datetime.now().isoformat()
        
    }

    # Write story data to JSON
    with open(story_data_file_path, 'w') as f:
        json.dump(story_data, f, indent=4)
    



create_story_data(story_type="Literature", 
                  story_title="To Kill a Mockingbird", 
                  story_author="Harper Lee",
                  story_protagonist="Scout Finch", 
                  story_year="1960", 
                  story_summary_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/to_kill_a_mockingbird_composite_data.json")