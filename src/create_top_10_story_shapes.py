from google.oauth2.service_account import Credentials
import gspread
import yaml
from story_shape import create_shape



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
sheet_id = "1LIZ6lfFwH7SWwbdwkR4rX5v36_DhI0Bx-L8vlw8pL2w"
spreadsheet = client.open_by_key(sheet_id)

# Access the first worksheet
worksheet = spreadsheet.sheet1

# Get all rows from the sheet
rows = worksheet.get_all_records()

for row in rows:
    # Extract input_path and output_path
    story_data_path = row.get("story_data_path")
    background_color = row.get("background_color")
    font_color = row.get("font_color")
    border_color = row.get("border_color")
    font = row.get("font")
    
    
    create_shape(story_data_path = story_data_path,
                    x_delta=0.015, #number of points in the line 
                    line_type = 'char', #values line or char
                    line_thickness = 10, #only used if line_type = line
                    line_color = font_color, #only used if line_type = line
                    font_style=font, #only used if line_type set to char
                    font_size= 8, #only used if line_type set to char
                    font_color = font_color, #only used if line_type set to char
                    background_type='solid', #values solid or transparent
                    background_value= background_color, #only used if background_type = solid
                    has_title = "YES", #values YES or NO
                    title_text = "", #optinal if left blank then will use story title as default
                    title_font_style = font, #only used if has_title = "YES"
                    title_font_size=24, #only used if has_title = "YES"
                    title_font_color = font_color, #only used if has_title = "YES"
                    title_padding = 0, #extra padding in pixels between bottom and title
                    gap_above_title=20, #padding in pixels between title and story shape
                    border=True, #True or False
                    border_thickness=60, #only applicable if border is set to True
                    border_color=border_color, #only applicable if border is set to True
                    width_in_inches = 6,  #design width size
                    height_in_inches = 6, #design width size
                    wrap_in_inches=1.5,  # for canvas print outs 
                    recursive_mode = True, #if you want to recurisvely generate story
                    recursive_loops = 1000, #the number of iterations 
                    output_format="png") #options png or svg

    #notes:
    #15x15 -- font_size = 72