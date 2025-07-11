from google.oauth2.service_account import Credentials
import gspread
import yaml
from story_data import create_story_data
from story_style import get_story_style
from story_shape import create_shape
import json 
import os
import re
import time 
import platform
from PIL import ImageFont
from googleapiclient.discovery import build


from matplotlib import font_manager
import sys

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

# Check if we are running in the Google Colab environment
if 'google.colab' in sys.modules:
    print("Running in Google Colab environment.")
    from google.colab import drive
    drive.mount('/content/drive')
    
    # Set the base directory to the project folder in your Google Drive
    BASE_DIR = '/content/drive/My Drive/'
    
else:
    print("Running in a local environment.")
    # Set the base directory to the project folder on your local machine
    # You will need to update this path based on where your Google Drive folder is located.
    # --- FIND YOUR LOCAL GOOGLE DRIVE PATH AND UPDATE THE LINE BELOW ---
    
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
PATHS['shapes_output'] = os.path.join(BASE_DIR, 'data', 'story_shapes')
PATHS['posters_output'] = os.path.join(BASE_DIR, 'data', 'posters')
PATHS['config'] = os.path.join(BASE_DIR, 'config.yaml')

# --- Automatically create output directories if they don't exist ---
os.makedirs(PATHS['story_data'], exist_ok=True)
os.makedirs(PATHS['shapes_output'], exist_ok=True)
os.makedirs(PATHS['posters_output'], exist_ok=True)

# --- Add the 'src' directory to the system path ---
# This allows your scripts to import from each other using "from llm import ..."
sys.path.append(PATHS['src'])

# --- Verify that the base directory exists ---
if not os.path.exists(BASE_DIR):
    raise FileNotFoundError(f"The base directory was not found at: {BASE_DIR}\n"
                            "Please check your path configuration for the current environment.")

print(f"\nProject Base Directory: {BASE_DIR}")
print("All paths configured successfully.")


import math # ensure math is imported if if component['space_to_modify'] >t already

def get_scaled_print_parameters(new_width_in, new_height_in, dpi=300):
    """
    Calculates scaled parameters for print products based on a new width and height,
    using an 8x10 print as the reference.

    Args:
        new_width_in (int): The width of the new print product in inches.
        new_height_in (int): The height of the new print product in inches.
        dpi (int): Dots per inch for pixel calculations.

    Returns:
        dict: A dictionary containing all necessary scaled parameters.
    """
    base_width_in = 8
    base_height_in = 10

    # Base parameters from the 8x10 print product
    base_params = {
        "line_thickness": 26,          # pixels (at 300 DPI for 8x10)
        "font_size": 12,               # points
        "title_font_size": 32,         # points
        "gap_above_title": 70,         # pixels (at 300 DPI for 8x10)
        "protagonist_font_size": 16,   # points
        "author_font_size": 16,        # points
        "top_text_font_size": 12,      # points (used if wrap_in_inches > 0)
        "bottom_text_font_size": 12,   # points (used if wrap_in_inches > 0)
        "top_and_bottom_text_band": 1.0, # inches (used if wrap_in_inches > 0)
        "border_thickness": 75,        # pixels (not used if has_border=False for prints)
        "wrap_in_inches": 0,           # Prints typically have no wrap
        "max_num_steps": 2,
        "step_k": 6,
        "has_border": True,           # Prints typically don't have a drawn border like canvas
        "fixed_margin_in_inches": 0.6
    }

    # Handle the 8x10 (or 10x8) case directly
    is_base_size_portrait = (new_width_in == base_width_in and new_height_in == base_height_in)
    is_base_size_landscape = (new_width_in == base_height_in and new_height_in == base_width_in) # e.g. 10x8

    if is_base_size_portrait or is_base_size_landscape:
        params_to_return = base_params.copy()
        params_to_return["width_in_inches"] = new_width_in
        params_to_return["height_in_inches"] = new_height_in
        return params_to_return

    # Scaling factor based on the shorter dimension relative to the base's shorter dimension (8 inches)
    base_ref_dim = min(base_width_in, base_height_in)  # 8 inches
    new_ref_dim = min(new_width_in, new_height_in)

    if new_ref_dim <= 0 or base_ref_dim <= 0: # Avoid division by zero or nonsensical scaling
        scaling_factor = 1.0
    else:
        scaling_factor = new_ref_dim / base_ref_dim

    scaled_params = {}

    # Scale font sizes (points) - apply minimums
    # scaled_params["font_size"] = max(6, round(base_params["font_size"] * scaling_factor))
    # scaled_params["title_font_size"] = max(10, round(base_params["title_font_size"] * scaling_factor))
    # scaled_params["protagonist_font_size"] = max(7, round(base_params["protagonist_font_size"] * scaling_factor))
    # scaled_params["author_font_size"] = max(7, round(base_params["author_font_size"] * scaling_factor))
    # scaled_params["top_text_font_size"] = max(6, round(base_params["top_text_font_size"] * scaling_factor))
    # scaled_params["bottom_text_font_size"] = max(6, round(base_params["bottom_text_font_size"] * scaling_factor))
    scaled_params["font_size"] = round(base_params["font_size"] * scaling_factor)
    scaled_params["title_font_size"] = round(base_params["title_font_size"] * scaling_factor)
    scaled_params["protagonist_font_size"] = round(base_params["protagonist_font_size"] * scaling_factor)
    scaled_params["author_font_size"] = round(base_params["author_font_size"] * scaling_factor)
    scaled_params["top_text_font_size"] = round(base_params["top_text_font_size"] * scaling_factor)
    scaled_params["bottom_text_font_size"] = round(base_params["bottom_text_font_size"] * scaling_factor)

    # Scale pixel-defined values based on general scaling_factor
    # scaled_params["line_thickness"] = max(10, round(base_params["line_thickness"] * scaling_factor))
    scaled_params["line_thickness"] = round(base_params["line_thickness"] * scaling_factor)

    # Scale gap_above_title proportionally to the title font size change (in pixels)
    base_title_font_px = base_params["title_font_size"] * (dpi / 96.0) # Points to pixels
    new_title_font_px = scaled_params["title_font_size"] * (dpi / 96.0)
    
    gap_font_ratio = new_title_font_px / base_title_font_px if base_title_font_px > 0 else scaling_factor
    # scaled_params["gap_above_title"] = max(15, round(base_params["gap_above_title"] * gap_font_ratio))
    scaled_params["gap_above_title"] = round(base_params["gap_above_title"] * gap_font_ratio)


    # Scale inch-defined values
    # scaled_params["top_and_bottom_text_band"] = max(0.25, base_params["top_and_bottom_text_band"] * scaling_factor)
    # scaled_params["fixed_margin_in_inches"] = max(0.25, base_params["fixed_margin_in_inches"] * scaling_factor)
    scaled_params["top_and_bottom_text_band"] = base_params["top_and_bottom_text_band"] * scaling_factor
    scaled_params["fixed_margin_in_inches"] = base_params["fixed_margin_in_inches"] * scaling_factor


    # Scale max_num_steps (integer, visual density)
    scaled_max_steps = base_params["max_num_steps"] * scaling_factor
    if scaled_max_steps < 1.5: # If new size is significantly smaller
        scaled_params["max_num_steps"] = 1
    else: # Allow it to scale up slightly, but often 2 is good for prints.
        scaled_params["max_num_steps"] = min(3, round(scaled_max_steps)) # Cap at 3 for prints

    # Parameters typically fixed for "print" products or directly copied
    scaled_params["step_k"] = base_params["step_k"]
    scaled_params["border_thickness"] = base_params["border_thickness"] # Not used if has_border=False
    scaled_params["has_border"] = base_params["has_border"]
    scaled_params["wrap_in_inches"] = base_params["wrap_in_inches"] # Should be 0 for prints

    # Assign new width and height
    scaled_params["width_in_inches"] = new_width_in
    scaled_params["height_in_inches"] = new_height_in
    
    return scaled_params

# # Load credentials from the YAML file
# def load_credentials_from_yaml(file_path):
#     with open(file_path, "r") as yaml_file:
#         config = yaml.safe_load(yaml_file)
#     return config["google_sheets"]

# CONFIG_FILE = "/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml"
# creds_data = load_credentials_from_yaml(CONFIG_FILE)

# Load credentials from the YAML file
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
sheet_id = "1C0CytarUcbUrRpqi5RK7MJUOb2DBR_bjQ_IeqcCi-Yw"
spreadsheet = client.open_by_key(sheet_id)
worksheet = spreadsheet.sheet1 # Access the first worksheet


# Get all rows from the sheet
rows = worksheet.get_all_records()

#loop through all rows but really should just be first row
for row in rows:
    print("starting...")
    start_time = time.perf_counter()
    # Assign each column value to a variable
    product = row.get("product")
    size = row.get("size")
    print(size)
    line_type = row.get("line_type")
    file_format = row.get("file_format")
    title = str(row.get("title"))
    author = row.get("author")
    protagonist = row.get("protagonist")
    year = row.get("year")
    summary_file = row.get("summary_file")
    background_color = row.get("background_color (optional)")
    font_color = row.get("font_color (optional)")
    #border_color = row.get("border_color (optional)")
    border_color = "FFFFFF"
    font = row.get("font (optional)")
    width = row.get("width (in) (optional)")
    height = row.get("height (in) (optional)")
    subtitle = row.get("subtitle (optional)")

    #if style not fully specified then get style for story
    story_style = {} # Initialize the dictionary
    design_rationale = "" # Initialize the design rationale
    if background_color == "" or font_color == "" or border_color == "" or font == "":

        story_style = get_story_style(
            config_path = PATHS['config'],
            story_title = title, 
            author = author,
            protagonist = protagonist, 
            llm_provider = "anthropic", #"google", #"openai",#, #"openai",, #"anthropic", #google", 
            llm_model = "claude-3-5-sonnet-latest"#"gemini-2.5-pro-preview-06-05", #o3-mini-2025-01-31", #"o4-mini-2025-04-16" #"gemini-2.5-pro-preview-05-06" #"o3-2025-04-16" #"gemini-2.5-pro-preview-05-06"#o3-2025-04-16"#"gemini-2.5-pro-preview-05-06" #"claude-3-5-sonnet-latest" #"gemini-2.5-pro-preview-03-25"
        )
        story_style = json.loads(story_style)
        design_rationale = story_style.get('design_rationale')

        print(design_rationale)

        if background_color == "":
            background_color = story_style.get('background_color')
            print("background color set to: ", background_color)
        else:
            design_rationale = "manuel override"
            print("background color manual override set to: ", background_color)

        if font_color == "":
            font_color = story_style.get('font_color')
            print("font color set to: ", font_color)
        else:
            design_rationale = "manuel override"
            print("font color manual override set to: ", font_color)

        if border_color == "":
            border_color = story_style.get('border_color')
            print("border color set to: ", border_color)
        else:
            design_rationale = "manuel override"
            print("border color manual override set to: ", border_color)

        if font == "":
            font = story_style.get('font')
            print("font set to: ", font)
        else:
            design_rationale = "manuel override"
            print("font manual override set to: ", font)
        
    else:
        print("story style provided")


    #CHECK ABOUT FONT
    if 'google.colab' in sys.modules:
        # 2. Use the `find_font` function to get the correct internal name
        #    (This function was created in the cell above)
        desired_family = font
        font = find_font(font) #find font is function that exists in collab notebook only

        # 3. Check if a font was found and then use it
        if font:
            print(f"Request: ('{desired_family}') -> Found best match: '{font}'")
            
        else:
            print(f"ERROR: Could not find a suitable font for '{desired_family}'"
                "Please check the library table in the cell above for available fonts.")
            #next create story data
    else:
        if font and not pango_font_exists(font):
            raise ValueError(f"'{font}' not found on this system.")


    # Normalize the title to replace curly apostrophes with straight ones
    title = title.replace("’", "'")  # Normalize typographic apostrophes
    title = title.replace(",", "")
    
    #/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/harry-potter-and-the-philosopher's-stone_harry-potter.json
    #/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/harry-potter-and-the-sorcerer's-stone_harry-potter_8x10.json
    
    #we should check if exsits first if not then create it 
    # story_data_output_path_base = "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/"
    # potential_story_data_file_path = title.lower().replace(' ', '-') + "_" + protagonist.lower().replace(' ', '-')
    # check_path = story_data_output_path_base + potential_story_data_file_path + ".json"
    
    # Check if story data exists first, if not then create it 
    potential_story_data_file_path = title.lower().replace(' ', '-') + "_" + protagonist.lower().replace(' ', '-')
    # Use the configured path
    check_path = os.path.join(PATHS['story_data'], potential_story_data_file_path + ".json")
    print(check_path)
    print("/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/harry-potter-and-the-sorcerer's-stone_harry-potter.json")

    if os.path.exists(check_path):
        story_data_path = check_path
        print("story data exists")
    else:
        #print("couldnt find")
        print("story data did not exist")
        story_data, story_data_path = create_story_data(config_path = PATHS['config'],
            summary_dir = PATHS['summaries'],
            summary_file=summary_file,
            author=author, 
            year=year, 
            protagonist=protagonist,
            #output_path = story_data_output_path_base,
            output_path = PATHS['story_data'], # <-- CORRECTED
            llm_provider = "google", #"google", #"openai",#, #"openai",, #"anthropic", #google", 
            llm_model = "gemini-2.5-pro"#"gemini-2.5-pro-preview-06-05", #o3-mini-2025-01-31", #"o4-mini-2025-04-16" #"gemini-2.5-pro-preview-05-06" #"o3-2025-04-16" #"gemini-2.5-pro-preview-05-06"#o3-2025-04-16"#"gemini-2.5-pro-preview-05-06" #"claude-3-5-sonnet-latest" #"gemini-2.5-pro-preview-03-25"
            )

    ### YOU JUST NEED 12x12 and then you shrinnk it down 
    # size     | 6x6 | 12x12 | 10x10 | 8x10
    # wrap     | 1.5 | 3     | 1.5   |  ?
    # t/b band | 1.5 | 1.5   | 1.5   |  ?
    # ----------------------------------
    # arc      | 8   | 16    | 14    |  12
    # title    | 24  | 48    | 40    |  32
    # protag   | 12  | 24    | 20    |  16
    # top      | 24  | 48    | 20    |  16
    # bottom   | 6   | 12    | 12    |  12
    #-----------------------------------
    # line     | 20  | 40    | 33    |  26
    # border   | ?   | 150   | 150   |  150
    # gap      | 20  | 40    | 33    |
    #-----------------------------------

    if product == "canvas" and size == "12x12":
        line_thickness = 40
        font_size = 16
        title_font_size = 48
        gap_above_title = 40
        protagonist_font_size = 24
        author_font_size = 24
        top_text = author + ", " + str(year)
        top_text_font_size = 48
        bottom_text_font_size = 12
        top_and_bottom_text_band = 1.5
        border_thickness = 150
        width_in_inches = 12
        height_in_inches = 12
        wrap_in_inches = 3
        max_num_steps = 3
        step_k = 10
        has_border = True
        fixed_margin_in_inches = 0.6
    elif product == "canvas" and size == "10x10":
        line_thickness = 33
        font_size = 14
        title_font_size = 40
        gap_above_title = 33
        protagonist_font_size = 20
        author_font_size = 20
        top_text = author + ", " + str(year)
        top_text_font_size = 20
        bottom_text_font_size = 12
        top_and_bottom_text_band = 1
        border_thickness = 150 #use thicker border
        width_in_inches = 10
        height_in_inches = 10
        wrap_in_inches = 1.5
        max_num_steps = 3
        step_k = 10
        has_border = True
        fixed_margin_in_inches = 0.6
    elif product == "print" and size == "8x10":

        total_chars_line1 = len(title) + len(protagonist)
        if total_chars_line1 > 45:
             title_font_size = 14
             protagonist_font_size = 10
             author_font_size = 10
        else:
            title_font_size = 20
            protagonist_font_size = 12
            author_font_size = 12
     

        line_thickness = 26
        font_size = 8
        gap_above_title = 70 #value was 26
        top_text = author + ", " + str(year)
        top_text_font_size = 8
        bottom_text_font_size = 8
        top_and_bottom_text_band = 1
        #border_thickness = 75 #use thinner border 
        border_thickness = 150 #use thinner border 
        width_in_inches = 8
        height_in_inches = 10
        wrap_in_inches = 0
        max_num_steps = 2
        step_k = 6
        #has_border = False
        has_border = True
        fixed_margin_in_inches = 0.6
    
    elif product == "print" and size == "custom":
        print_params = get_scaled_print_parameters(width, height)
        print(print_params)
        
        line_thickness = print_params["line_thickness"]
        font_size = print_params["font_size"]
        title_font_size = print_params["title_font_size"]
        gap_above_title = print_params["gap_above_title"]
        protagonist_font_size = print_params["protagonist_font_size"]
        author_font_size = print_params["author_font_size"]
        top_text_font_size = print_params["top_text_font_size"]
        bottom_text_font_size = print_params["bottom_text_font_size"]
        top_and_bottom_text_band = print_params["top_and_bottom_text_band"]
        border_thickness = print_params["border_thickness"]
        width_in_inches = print_params["width_in_inches"]
        height_in_inches = print_params["height_in_inches"]
        wrap_in_inches = print_params["wrap_in_inches"]
        max_num_steps = print_params["max_num_steps"]
        step_k = print_params["step_k"]
        has_border = print_params["has_border"]
        fixed_margin_in_inches = print_params["fixed_margin_in_inches"]


        top_text = ""

    else:
        raise ValueError


    print("creating story shape")
    new_story_data_path, story_shape_path = create_shape(
                    config_path = PATHS['config'],
                    output_dir = PATHS['shapes_output'], # <-- ADD THIS LINE
                    story_data_dir=PATHS['story_data'],      # For reading/writing data files
                    story_data_path = story_data_path,
                    product = product,
                    x_delta= 0.015,#0.015, #number of points in the line 
                    step_k = step_k, #step-by-step steepness; higher k --> more steepness; values = 3, 4.6, 6.9, 10, 15
                    max_num_steps = max_num_steps,
                    line_type = line_type, #values line or char
                    line_thickness = line_thickness, #only used if line_type = line
                    line_color = font_color, #only used if line_type = line
                    font_style= font, #only used if line_type set to char
                    font_size= font_size, #only used if line_type set to char
                    font_color = font_color, #only used if line_type set to char
                    background_type='solid', #values solid or transparent
                    background_value = background_color, #only used if background_type = solid
                    has_title = "YES", #values YES or NO
                    title_text = "", #optinal if left blank then will use story title as default
                    title_font_style = font, #only used if has_title = "YES"
                    title_font_size=title_font_size, #only used if has_title = "YES"
                    title_font_color = font_color, #only used if has_title = "YES"
                    title_font_bold = False, #can be True or False
                    title_font_underline = False, #can be true or False
                    title_padding = 0, #extra padding in pixels between bottom and title
                    gap_above_title=gap_above_title, #padding in pixels between title and story shape
                    protagonist_text = protagonist, #if you leave blank will include protognaist name in lower right corner; can get rid of by just setting to " ", only works if has title is true
                    protagonist_font_style = font,
                    protagonist_font_size=protagonist_font_size, 
                    protagonist_font_color=font_color,
                    protagonist_font_bold = False, #can be True or False
                    protagonist_font_underline = False, #can be True or False

                    author_text=subtitle, # Optional, defaults to story_data['author']
                    author_font_style=font, # Defaults to title font style if empty
                    author_font_size=author_font_size, # Suggest smaller than title
                    author_font_color=font_color, # Use hex, defaults to title color
                    author_font_bold=False,
                    author_font_underline=False,
                    author_padding=5, 

                    top_text = top_text, #only applies when wrapped > 0; if "" will default to author, year
                    top_text_font_style = font,
                    top_text_font_size = top_text_font_size,
                    top_text_font_color = font_color,
                    bottom_text = "", #only applies when wrapped > 0; if "" will default to "Shapes of Stories"
                    bottom_text_font_style = "Sans",
                    bottom_text_font_size = bottom_text_font_size,
                    bottom_text_font_color = "#000000",
                    top_and_bottom_text_band = top_and_bottom_text_band, #this determines the band which top and center text is centered on above/below design; if you want to center along full wrap in inches set value to wrap_in_inches else standard is 1.5 
                    border=has_border, #True or False
                    border_thickness= border_thickness, #only applicable if border is set to True
                    border_color=border_color, #only applicable if border is set to True
                    width_in_inches = width_in_inches,  #design width size
                    height_in_inches = height_in_inches, #design width size
                    wrap_in_inches=wrap_in_inches,  # for canvas print outs 
                    wrap_background_color = border_color, #wrapped in inches part color only relevant when wrap_in_inches > 0 inc
                    fixed_margin_in_inches = fixed_margin_in_inches, #fixed margins for output
                    recursive_mode = True, #if you want to recurisvely generate story
                    recursive_loops = 1000, #the number of iterations 
                    llm_provider = "anthropic",#"groq",#"openai", #anthropic",#"google" #for generating descriptors
                    llm_model = "claude-3-5-sonnet-latest",#"meta-llama/llama-4-scout-17b-16e-instruct",#"gpt-4.1-2025-04-14", #"claude-3-5-sonnet-latest",#"gemini-2.5-pro-preview-03-25", #"claude-3-5-sonnet-latest", #for generating descriptors 
                    #llm_provider = "google", #"anthropic", #google", 
                    #llm_model = "gemini-2.5-pro-preview-05-06", #"claude-3-5-sonnet-latest" #"gemini-2.5-pro-preview-03-25"
                    output_format=file_format
                ) #options png or svg
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"The script took {elapsed_time:.4f} seconds to execute.")

   # --- NEW CODE TO UPDATE THE CATALOGUE ---
try:
    print("Opening Catalogue spreadsheet...")
    catalogue_sheet_id = "1V63O3KwADfTKivRVnz_YfONmWu8kmfwk_mgvu7cdGLY"
    catalogue_spreadsheet = client.open_by_key(catalogue_sheet_id)
    catalogue_worksheet = catalogue_spreadsheet.worksheet("To-Be Published")

    print("Fetching Google Drive links for created files...")

    # Get just the filenames from the full local paths
    story_data_filename = os.path.basename(new_story_data_path)
    shape_filename = os.path.basename(story_shape_path)
    summary_filename = os.path.basename(summary_file)

    # Call our new function to get the web URL for each file
    # This might take a minute as it waits for files to sync to the cloud.
    story_data_url = get_google_drive_link(drive_service, story_data_filename)
    shape_image_url = get_google_drive_link(drive_service, shape_filename)
    summary_filename_url = get_google_drive_link(drive_service, summary_filename)

    print("Updating Catalogue...")

    design_style_info = story_style.get('design_rationale', 'N/A')

    # Assemble the row data with the new clickable URLs
    # IMPORTANT: Make sure this order perfectly matches your Google Sheet columns
    new_row_data = [
        product,
        size,
        line_type,
        file_format,
        title,
        subtitle,
        author,
        protagonist,
        year,
        design_style_info,
        background_color,
        font_color,
        border_color,
        font,
        summary_filename_url, # <-- Using the new clickable URL
        story_data_url,     # <-- Using the new clickable URL
        shape_image_url,     # <-- Using the new clickable URL
        summary_file, #local path
        new_story_data_path, #local path
        story_shape_path    #<--- local path of story shape (for uploading into printify)
    ]

    # Append the new row to the Catalogue worksheet
    catalogue_worksheet.append_row(new_row_data)
    
    print("Successfully updated Catalogue.")

except gspread.exceptions.SpreadsheetNotFound:
    print("--- CATALOGUE ERROR ---")
    print("The spreadsheet named 'Catalogue' was not found.")
    print("Please ensure the ID is correct and that it has been shared with your service account.")
except Exception as e:
    print(f"An error occurred while updating the Catalogue: {e}")
# --- END OF NEW CODE ---