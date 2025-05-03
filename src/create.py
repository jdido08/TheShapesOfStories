from google.oauth2.service_account import Credentials
import gspread
import yaml
from story_data import create_story_data
from story_style import get_story_style
from story_shape import create_shape
import json 
import os
import re

# Load credentials from the YAML file
def load_credentials_from_yaml(file_path):
    with open(file_path, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config["google_sheets"]

CONFIG_FILE = "/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml"
creds_data = load_credentials_from_yaml(CONFIG_FILE)

# Define the correct scope
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# Create credentials with the correct scope
credentials = Credentials.from_service_account_info(creds_data, scopes=SCOPES)

# Authorize and create a client
client = gspread.authorize(credentials)

# Open the Google Sheet by its ID
#link https://docs.google.com/spreadsheets/d/1T0ThSHKK_sMIKTdwC14WZoWFNFD3dU7xIheQ5AF9NLU/edit?usp=sharing
sheet_id = "1T0ThSHKK_sMIKTdwC14WZoWFNFD3dU7xIheQ5AF9NLU"
spreadsheet = client.open_by_key(sheet_id)
worksheet = spreadsheet.sheet1 # Access the first worksheet


# Get all rows from the sheet
rows = worksheet.get_all_records()

#loop through all rows but really should just be first row
for row in rows:
    print("starting...")
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
    summary_path = row.get("summary_path")
    background_color = row.get("background_color (optional)")
    font_color = row.get("font_color (optional)")
    border_color = row.get("border_color (optional)")
    font = row.get("font (optional)")

    #if style not fully specified then get style for story
    if background_color == "" or font_color == "" or border_color == "" or font == "":

        story_style = get_story_style(
            story_title = title, 
            author = author,
            protagonist = protagonist, 
            llm_provider = "google", #"anthropic",  
            llm_model = "gemini-2.5-pro-preview-03-25"
        )
        story_style = json.loads(story_style)
        design_rationale = story_style.get('design_rationale')

        print(design_rationale)

        if background_color == "":
            background_color = story_style.get('background_color')
            print("background color set to: ", background_color)
        else:
            print("background color manual override set to: ", background_color)

        if font_color == "":
            font_color = story_style.get('font_color')
            print("font color set to: ", font_color)
        else:
            print("font color manual override set to: ", font_color)

        if border_color == "":
            border_color = story_style.get('border_color')
            print("border color set to: ", border_color)
        else:
            print("border color manual override set to: ", border_color)

        if font == "":
            font = story_style.get('font')
            print("font set to: ", font)
        else:
            print("font manual override set to: ", font)
        
    else:
        print("story style provided")

    
    #next create story data

    # Normalize the title to replace curly apostrophes with straight ones
    title = title.replace("’", "'")  # Normalize typographic apostrophes
    title = title.replace(",", "")
    
    #we should check if exsits first if not then create it 
    story_data_output_path_base = "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/story_data/"
    potential_story_data_file_path = title.lower().replace(' ', '-') + "_" + protagonist.lower().replace(' ', '-')
    check_path = story_data_output_path_base + potential_story_data_file_path + ".json"
    print(check_path)
    if os.path.exists(check_path):
        story_data_path = check_path
        print("story data exists")
    else:
        #print("couldnt find")
        print("story data did not exist")
        story_data, story_data_path = create_story_data(
            input_path=summary_path,
            author=author, 
            year=year, 
            protagonist=protagonist,
            output_path = story_data_output_path_base,
            llm_provider="google",
            llm_model="gemini-2.5-pro-preview-03-25"
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
        line_thickness = 26
        font_size = 12
        title_font_size = 32 #value is 32, other values: 26, 22, 20 (very small)
        gap_above_title = 70 #value was 26
        protagonist_font_size = 16
        top_text = author + ", " + str(year)
        top_text_font_size = 12
        bottom_text_font_size = 12
        top_and_bottom_text_band = 1
        border_thickness = 75 #use thinner border 
        width_in_inches = 8
        height_in_inches = 10
        wrap_in_inches = 0
        max_num_steps = 2
        step_k = 6
        has_border = False
        fixed_margin_in_inches = 0.6
    else:
        raise ValueError


    print("creating story shape")
    new_story_data_path, story_shape_path = create_shape(story_data_path = story_data_path,
                    product = product,
                    x_delta=0.015, #number of points in the line 
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
                    recursive_loops = 500, #the number of iterations 
                    llm_provider = "google",#"anthropic", #for generating descriptors
                    llm_model = "gemini-2.5-pro-preview-03-25", #"claude-3-5-sonnet-latest", #for generating descriptors 
                    output_format=file_format
                ) #options png or svg
    

