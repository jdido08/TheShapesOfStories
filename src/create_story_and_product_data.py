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

# This dictionary will hold all our configured paths
PATHS = {}

local_drive_path = os.path.expanduser('~/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive')
if not os.path.exists(local_drive_path): # Fallback for older Google Drive versions
    local_drive_path = '/Volumes/GoogleDrive/My Drive'

BASE_DIR = local_drive_path

# --- Define all other paths relative to the base directory ---
PATHS['src'] = os.path.join(BASE_DIR, 'src')
PATHS['summaries'] = os.path.join(BASE_DIR, 'summaries')
PATHS['story_data'] = os.path.join(BASE_DIR, 'story_data')
PATHS['product_data'] = os.path.join(BASE_DIR, 'product_data')
PATHS['product_designs'] = os.path.join(BASE_DIR, 'product_designs')
PATHS['shapes_output'] = os.path.join(BASE_DIR, 'story_shapes')
PATHS['supporting_designs'] = os.path.join(BASE_DIR, 'supporting_designs')
PATHS['product_mockups'] = os.path.join(BASE_DIR, 'product_mockups')
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


def create_story_data(story_type, story_title, story_author,story_protagonist, story_year, story_summary_path):
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
    print("✅ Story Style")
    
    #check if font supported in local environment
    if design_font and not pango_font_exists(design_font):
        raise ValueError(f"'{design_font}' not found on this system.")
    

    # save story data back as json 
    story_data = {
        "title": story_title,
        "author": story_author,
        "protagonist": story_protagonist, 
        "year": story_year,
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
        "story_type": story_type,
        "summary": story_summary,
        "story_component_grades":story_component_grades,
        "llm_models": {
            "story_components": story_components_llm_model,
            "story_components_grade": story_components_grader_llm_model,
            "story_default_style": story_style_llm_model
        },
        "story_slug":story_data_file_name,
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
    story_metadata_llm_model = "claude-3-5-sonnet-latest"
    get_story_metadata(
        story_json_path=story_data_file_path,
        use_llm="on",
        config_path=PATHS['config'],
        llm_provider=story_metadata_llm_provider,
        llm_model=story_metadata_llm_model
    )
    print("✅ Story MetaData")
    print("")
    

    




# Examle Call 		
# create_story_data(story_type="Literature", 
#                   story_title="The Tell-Tale Heart", 
#                   story_author="Edgar Allan Poe",
#                   story_protagonist="The Narrator", 
#                   story_year="1843", 
#                   story_summary_path="/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/summaries/the_tell-tale_heart_composite_data.json")


# CREATE PRODUCT DATA
# INPUTS:
# - story data json 
# - product type -> print | t-shirt | canvas | etc.. 
# - product size (if applicable)
# - product style / colors (if different from default)
#
# LOGIC:
# - create product design variant e.g. print-11x14
# - ensure shape the same (make sure you're using modified times/values)
# - grade story data text
# - create product description
# - create product metafields
# - create product mockups 
# - create line and svg variants

from product_shape import create_shape
from product_color import map_hex_to_simple_color
from story_shape_category import get_story_symbolic_and_archetype
from product_description import create_product_description
from product_text_accuracy import assess_arc_text
from product_mockups import create_mockups

def create_product_data(story_data_path, product_type="", product_size="", product_style=""):

    #check if story_data path exists and if so then open data 
    if not os.path.exists(story_data_path):
        print(f"Error: Analysis file not found at {story_data_path}")
        return
    with open(story_data_path, 'r') as f:
        story_data = json.load(f)

    #annoucen which product you're creating 
    print("Product: ", story_data.get("title"), " - ", story_data.get("protagonist"), " - ", product_type, " - ", product_size)
    
    
    #determine product style
    if product_style == "": #if product_style left empty that use default
        background_color_hex = story_data.get("default_style", {}).get("background_color_hex")
        font_color_hex = story_data.get("default_style", {}).get("font_color_hex")
        font = story_data.get("default_style", {}).get("font")
    else: #else set product style but not supporting that for the moment 
        print(f"Error: Product (currently) only supports using default story styles")
        return

    # right now only print 11x14 is support for product types
    if product_type != "print" and product_type != "11x14":
        print(f"Error: only print 11x14 products are supported at this time but you requested {product_type} {product_size}")
        return
    

    title = story_data.get("title")
    protagonist = story_data.get("protagonist")
    author = story_data.get("author")
    year = story_data.get("year")

    if product_type == "print" and product_size == "11x14":
        product_data_path, product_design_path = create_print_11x14_product_data(
            story_data_path=story_data_path,
            title=title,
            protagonist=protagonist,
            author=author,
            year=year,
            background_color_hex=background_color_hex,
            font_color_hex=font_color_hex,
            font=font,
            line_type = "char",
            output_format="png",
            output_dir=PATHS['product_designs']
        )
    else:
        print("❌ ERROR: Only print 11x14 supported today")
        return
    

    #open product data to save story data path 
    with open(product_data_path, 'r') as f:  #open product json data that was just created
        product_data = json.load(f)
    product_data['story_data_path'] = story_data_path
    product_data['product_design_path'] = product_design_path
    with open(product_data_path, "w", encoding="utf-8") as f:     # save it back to the same file
        json.dump(product_data, f, ensure_ascii=False, indent=2)
        f.write("\n")  # optional newline at EOF
    time.sleep(2)

    # Compare product shape to make sure it's the same as the story -- product shapes can change slightly during product creations
    with open(product_data_path, 'r') as f:  #open product json data that was just created
        product_data = json.load(f)
    product_story_components = product_data.get("story_components")
    product_symbolic_rep,  product_archetype = get_story_symbolic_and_archetype(product_story_components)
    if product_symbolic_rep != story_data.get("shape_symbolic_representation"):
        print("❌ Product Shape Failed")
        print("ERROR: Product and Data Symbolic Represensation Data do NOT EQUAL for {title}")
        print(f"Story Symbolic Rep: {story_data.get('shape_symbolic_representation')}")
        print(f"Product Symbolic Rep: {product_symbolic_rep}")
        return 
    if product_archetype != story_data.get("shape_archetype"):
        print("❌ Product Shape Failed")
        print("ERROR: Product and Data Shape Archetypes do NOT EQUAL for {title}")
        print(f"Story Shape Archetype: {story_data.get('shape_archetype')}")
        print(f"Product Shape Archetype: {product_archetype}")
        return 
    print("✅ Product Shape matches Story Shape")


    #description and save to product path
    llm_provider_product_description = "google"
    llm_model_product_description = "gemini-2.5-pro"
    # create_product_description(
    #     image_path=product_design_path,
    #     story_json_or_path=product_data_path,
    #     config_path=PATHS['config'],
    #     llm_provider = llm_provider_product_description,
    #     llm_model = llm_model_product_description
    # )
    # print("✅ Product Description")

    
    #grad story text
    llm_provider_assess_arc_text = "anthropic"
    llm_model_assess_arc_text = "claude-sonnet-4-20250514"
    # assess_arc_text(
    #     generated_analysis_path=product_data_path,
    #     config_path=PATHS['config'],
    #     llm_provider=llm_provider_assess_arc_text,
    #     llm_model=llm_model_assess_arc_text,
    # )
    # #need to reopen product data to assess whether grade passing or not
    # with open(product_data_path, 'r') as f:  #open product json data that was just created
    #     product_data = json.load(f)
    # final_grade = product_data["text_quality_assessment"]["text_accuracy_assessment"].get("final_grade")
    # if final_grade in ["A", "B"]: #need to think about whether I want to accept any Bs
    #     print("✅ Product Text Passed; Grade: ", final_grade)
    # else:
    #     print("❌ Product Text Failed; Grade: ", final_grade)


    # create_mockups(
    #     product_data_path=product_data_path,
    #     product_design_path=product_design_path,
    #     mockup_list=["11x14_poster","11x14_table", "11x14_wall", "3x_11x14_wall"],
    #     output_dir=PATHS['product_mockups'] 
    # )
    # print("✅ Product Mockups")



    #create supporting product designs -- line and svg versions: line - png, line - svg, char - svg
    supporting_designs = [
         {
            "line_type":"char",
            "output_format":"png"
        },
        {
            "line_type":"line",
            "output_format":"png"
        },
        {
            "line_type":"line",
            "output_format":"svg"
        },
        {
            "line_type":"char",
            "output_format":"svg"
        }
    ]
    supporting_design_file_paths = []

    with open(product_data_path, 'r') as f:  #open product json data that was just created
        product_data = json.load(f)
    if product_type == "print" and product_size == "11x14":
        for supporting_design in supporting_designs:
            product_data_path, product_design_path = create_print_11x14_product_data(
                story_data_path=story_data_path,
                title=title,
                protagonist=protagonist,
                author=author,
                year=year,
                background_color_hex=background_color_hex,
                font_color_hex=font_color_hex,
                font=font,
                line_type = supporting_design['line_type'],
                output_format=supporting_design['output_format'],
                output_dir=PATHS['supporting_designs']
            )
            supporting_design_file_paths.append(product_design_path)
            print("✅ ", supporting_design['line_type'], " - ", supporting_design['output_format'])
    else:
        print("ERROR: Only print 11x14 supported today")
        return
    
    #make final saves to product_data josn
    product_data['all_design_file_paths'] = supporting_design_file_paths
    product_data['llm_models']['product_description'] = llm_model_product_description
    product_data['llm_models']['assess_arc_text'] = llm_model_assess_arc_text
    product_data['product_type'] = product_type
    product_data['product_create_timestamp'] = datetime.now().isoformat()
    with open(product_data_path, "w", encoding="utf-8") as f:     # save it back to the same file
        json.dump(product_data, f, ensure_ascii=False, indent=2)
        f.write("\n")  # optional newline at EOF
    time.sleep(2)


    #FINAL THING SAVE LINK TO PRODUCT DATA IN STORY DATA
    with open(story_data_path, 'r') as f:
        story_data = json.load(f)
    story_data_products = story_data.get('products', {})
    story_data_products[product_data['product_slug']] = product_data_path
    story_data['products'] = story_data_products
    with open(story_data_path, "w", encoding="utf-8") as f:     # save it back to the same file
        json.dump(story_data, f, ensure_ascii=False, indent=2)
        f.write("\n")  # optional newline at EOF
    time.sleep(1)
    print("✅ story data updated w/ product data path")


    

    # Create Mockups
    # Mockups:
    #   1. 11x14 Poster w/ Paper Clips
    #   2. 11x14 Frame on Table
    #   3. 11x14 Frame on Wall 
    #   4. 3X 11x14 Frames on Wall 
    # Inputs:
    # - image file
    # - print 11x14 config file --> all details for 11x14 mockups; so could change out for other product types
    # Logic:
    # - create mockups 
    # Output:
    # - png file in new folder (mockups)
    # - add links to mockup files back into product data "mockup_links" = {}

    #figure out 2 - 4 and then circle back to #1 baecause that mockup has a different creation process.

    
    #TO DOS:
    # product metafields --> this might actually be better as a story
    # mockups
    # create line png, char svg, line svg, 




def create_print_11x14_product_data(story_data_path, title, protagonist, author, year, background_color_hex, font_color_hex,font, line_type, output_format, output_dir):       

    total_chars_line1 = len(title) + len(protagonist)
    if total_chars_line1 <= 38:
        title_font_size       = 27
        protagonist_font_size = 16
        author_font_size      = 16
    elif total_chars_line1 <= 65:
        title_font_size       = 25
        protagonist_font_size = 15
        author_font_size      = 15
    elif total_chars_line1 <= 85:
        title_font_size       = 19
        protagonist_font_size = 14
        author_font_size      = 14
    else:
        title_font_size       = 18
        protagonist_font_size = 13
        author_font_size      = 13

    #FIX SETTINGS
    line_thickness = 38
    font_size = 12
    gap_above_title = 102 #value was 26
    top_text = author + ", " + str(year)
    top_text_font_size = 12
    bottom_text_font_size = 12
    top_and_bottom_text_band = 1
    border_thickness = 0.5 # this is in inces 360 #600 #300 #360 ## --> (360/300)/2 DPI --> 0.6 inches OR (300/300 DPI)/2 --> 0.5 in 
    width_in_inches = 11
    height_in_inches = 14
    wrap_in_inches = 0
    max_num_steps = 2
    step_k = 6
    has_border = True
    fixed_margin_in_inches = 0.85  #1.25 #0.75 #0.85 
    border_color = "#FFFFFF" # --> manually set border to be white

        #FINAL DECISION:
        # Fixed Margins in Inches = 0.85
        # border_thickness = 360 --> 0.6 inches 
        # space between border and text = 0.2 = 0.85 - 0.6
        # but not that I have special logic in product_shape to make sure space between border and text on left, right, and top are 0.4
        #note that:
        #border thickness is in pixels and apparently half of it gets clipped (idk why) so with 300 DPI --> (150/300) --> 0.25
        #fixed_margin_in_inches is space between edge of print and where text begins
        #space between white edge and text is fixed_margin_in_inches -(border_thickness/300)
        #so if we want ~0.25in between white border and text AND a 0.6 in white border that means
        #border thickness = 

    #I need to think about this because I want re-run this a couple times:
    # 1.) char png
    # 2.) line png
    # 3.) char svg
    # 4.) line svg
    print("creating story shape")
    product_data_path, product_design_path = create_shape(
                    config_path = PATHS['config'],
                    output_dir = output_dir,        # where to save designs
                    story_data_dir=PATHS['product_data'],      # For reading/writing data files
                    story_data_path = story_data_path,
                    product = "print",
                    x_delta= 0.015,#0.015, #number of points in the line 
                    step_k = step_k, #step-by-step steepness; higher k --> more steepness; values = 3, 4.6, 6.9, 10, 15
                    max_num_steps = max_num_steps,
                    line_type = line_type, #values line or char
                    line_thickness = line_thickness, #only used if line_type = line
                    line_color = font_color_hex, #only used if line_type = line
                    font_style= font, #only used if line_type set to char
                    font_size= font_size, #only used if line_type set to char
                    font_color = font_color_hex, #only used if line_type set to char
                    background_type='solid', #values solid or transparent
                    background_value = background_color_hex, #only used if background_type = solid
                    has_title = "YES", #values YES or NO
                    title_text = "", #optinal if left blank then will use story title as default
                    title_font_style = font, #only used if has_title = "YES"
                    title_font_size=title_font_size, #only used if has_title = "YES"
                    title_font_color = font_color_hex, #only used if has_title = "YES"
                    title_font_bold = False, #can be True or False
                    title_font_underline = False, #can be true or False
                    title_padding = 0, #extra padding in pixels between bottom and title
                    gap_above_title=gap_above_title, #padding in pixels between title and story shape
                    protagonist_text = protagonist, #if you leave blank will include protognaist name in lower right corner; can get rid of by just setting to " ", only works if has title is true
                    protagonist_font_style = font,
                    protagonist_font_size=protagonist_font_size, 
                    protagonist_font_color=font_color_hex,
                    protagonist_font_bold = False, #can be True or False
                    protagonist_font_underline = False, #can be True or False

                    author_text=author, # Optional, defaults to story_data['author']
                    author_font_style=font, # Defaults to title font style if empty
                    author_font_size=author_font_size, # Suggest smaller than title
                    author_font_color=font_color_hex, # Use hex, defaults to title color
                    author_font_bold=False,
                    author_font_underline=False,
                    author_padding=5, 

                    top_text = top_text, #only applies when wrapped > 0; if "" will default to author, year
                    top_text_font_style = font,
                    top_text_font_size = top_text_font_size,
                    top_text_font_color = font_color_hex,
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
                    recursive_loops = 10000, #the number of iterations 
                    llm_provider = "anthropic",#"groq",#"openai", #anthropic",#"google" #for generating descriptors
                    llm_model = "claude-3-5-sonnet-latest",#"meta-llama/llama-4-scout-17b-16e-instruct",#"gpt-4.1-2025-04-14", #"claude-3-5-sonnet-latest",#"gemini-2.5-pro-preview-03-25", #"claude-3-5-sonnet-latest", #for generating descriptors 
                    #llm_provider = "google", #"anthropic", #google", 
                    #llm_model = "gemini-2.5-pro-preview-05-06", #"claude-3-5-sonnet-latest" #"gemini-2.5-pro-preview-03-25"
                    output_format=output_format #options png or svg
                ) 
    return product_data_path, product_design_path 



    
# Example 
create_product_data(story_data_path="/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/story_data/romeo-and-juliet-juliet.json",
                    product_type="print", 
                    product_size="11x14", 
                    product_style="")








# example_stories = [
#     {
#         "story_type": "Literature",
#         "story_title": "The Great Gatsby",
#         "story_author": "F. Scott Fitzgerald",
#         "story_protagonist": "Jay Gatsby",
#         "story_year": "1925",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/the_great_gatsby_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Pride and Prejudice",
#         "story_author": "Jane Austen",
#         "story_protagonist": "Elizabeth Bennet",
#         "story_year": "1813",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/pride_and_prejudice_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Moby-Dick",
#         "story_author": "Herman Melville",
#         "story_protagonist": "Ishmael",
#         "story_year": "1851",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/moby_dick_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "To Kill a Mockingbird",
#         "story_author": "Harper Lee",
#         "story_protagonist": "Scout Finch",
#         "story_year": "1960",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/to_kill_a_mockingbird_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "1984",
#         "story_author": "George Orwell",
#         "story_protagonist": "Winston Smith",
#         "story_year": "1949",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/1984_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Alice Adventures in Wonderland",
#         "story_author": "Lewis Carroll",
#         "story_protagonist": "Alice",
#         "story_year": "1865",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/alice_in_wonderland_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "The Catcher in the Rye",
#         "story_author": "J.D. Salinger",
#         "story_protagonist": "Holden Caulfield",
#         "story_year": "1951",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/the_catcher_in_the_rye_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Dune",
#         "story_author": "Frank Herbert",
#         "story_protagonist": "Paul Atreides",
#         "story_year": "1965",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/dune_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "The Alchemist",
#         "story_author": "Paulo Coelho",
#         "story_protagonist": "Santiago",
#         "story_year": "1988",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/the_alchemist_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Frankenstein",
#         "story_author": "Mary Shelley",
#         "story_protagonist": "Victor Frankenstein",
#         "story_year": "1818",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/frankenstein_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Romeo and Juliet",
#         "story_author": "William Shakespeare",
#         "story_protagonist": "Juliet",
#         "story_year": "1597",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/romeo_and_juliet_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Dracula",
#         "story_author": "Bram Stoker",
#         "story_protagonist": "Jonathan Harker",
#         "story_year": "1897",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/dracula_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "The Adventures of Huckleberry Finn",
#         "story_author": "Mark Twain",
#         "story_protagonist": "Huckleberry Finn",
#         "story_year": "1884",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/the_adventures_of_huckleberry_finn_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "Little Women",
#         "story_author": "Louisa May Alcott",
#         "story_protagonist": "Jo March",
#         "story_year": "1868",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/little_women_composite_data.json"
#     },
#     {
#         "story_type": "Literature",
#         "story_title": "The Old Man and the Sea",
#         "story_author": "Ernest Hemingway",
#         "story_protagonist": "Santiago",
#         "story_year": "1952",
#         "story_summary_path": "/Users/johnmikedidonato/Projects/TheShapesOfStories/data/summaries/the_old_man_and_the_sea_composite_data.json"
#     }
# ]


# for story in example_stories:
#     create_story_data(story_type=story['story_type'], 
#                   story_title=story['story_title'], 
#                   story_author=story['story_author'], 
#                   story_protagonist=story['story_protagonist'], 
#                   story_year=story['story_year'], 
#                   story_summary_path=story['story_summary_path'])


# example_story_data = [
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/little-women-jo-march.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/dracula-jonathan-harker.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/romeo-and-juliet-juliet.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/frankenstein-victor-frankenstein.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-alchemist-santiago.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/dune-paul-atreides.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-catcher-in-the-rye-holden-caulfield.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/alice-adventures-in-wonderland-alice.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/1984-winston-smith.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/moby-dick-ishmael.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/pride-and-prejudice-elizabeth-bennet.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-great-gatsby-jay-gatsby.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/to-kill-a-mockingbird-scout-finch.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-old-man-and-the-sea-santiago.json",
#     "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/data/story_data/the-adventures-of-huckleberry-finn-huckleberry-finn.json"

# ]




# for story_data_path in example_story_data:
#     create_product_data(story_data_path=story_data_path,
#                         product_type="print", 
#                         product_size="11x14", 
#                         product_style="")
