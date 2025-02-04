from google.oauth2.service_account import Credentials
import gspread
import yaml
from story_data import create_story_data

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


# Access a specific worksheet by name
#worksheet_name = "YourTabName"  
#worksheet = spreadsheet.worksheet(worksheet_name) # Change this to the actual tab name
worksheet = spreadsheet.sheet1 # Access the first worksheet


# Get all rows from the sheet
rows = worksheet.get_all_records()

for row in rows:
    # Extract input_path and output_path
    input_path = row.get("input_path")
    output_path = row.get("output_path")
    
    # Ensure both values exist before calling the function
    if input_path and output_path:
        create_story_data(input_path=input_path, output_path=output_path)
    else:
        print(f"Skipping row due to missing data: {row}")
