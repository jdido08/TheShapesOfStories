from google.oauth2.service_account import Credentials
import gspread
import yaml
from story_style import get_story_style #move to this sheet
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
#   - story components
#   - default style (color + font)
#   - validation of story components
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

def analyze_story(config_path, author_name, story_title, protagonist, story_summary, llm_provider, llm_model):
    

    # The user_message includes placeholders that will be replaced by the function arguments
    prompt_template = """You are a world-class literary scholar and expert in story analysis. Your task is to analyze a story through the emotional journey of {protagonist}. Please carefully read and analyze the following story summary:

<author_name>
{author_name}
</author_name>

<story_title>
{story_title}
</story_title>

<protagonist>
{protagonist}
</protagonist>

<story_summary>
{story_summary}
</story_summary>

## Framework Overview:
1. Story Timeline: The narrative is viewed on a scale from 0 to 100, representing the percentage of progress through the story.
2. Story Components: The story is segmented into components defined by {protagonist}'s emotional journey.
3. Continuity: Each story component starts where the previous one ended, ensuring a seamless emotional journey.
4. Emotional Arcs: {protagonist}'s emotional journey throughout each story component can vary in a range from euphoric (+10) to depressed (-10), based on their direct experiences and reactions to events.


## Emotional Arcs
### Types of Emotional Arcs:
1. Increase: The protagonist's emotional state improves by the end of the arc.
2. Decrease: The protagonist's emotional state worsens by the end of the arc.
3. Flat: The protagonist's emotional state remains unchanged by the end of the arc.

### Specific Emotional Arc Patterns:
1. Step-by-Step Increase/Decrease: Emotions change in distinct, noticeable stages
   Example: A character moving from fear (-5) to uncertainty (-2) to hope (+2) to joy (+6)
2. Linear Increase/Decrease: Consistent, steady change in emotional state
   Example: A character's growing dread as they approach danger, declining steadily from +3 to -4
3. Gradual-to-Rapid Increase/Decrease: Change starts slowly, then accelerates
   Example: A slow build of suspicion that suddenly turns to shocking realization
4. Rapid-to-Gradual Increase/Decrease: Change starts quickly, then slows down
   Example: An immediate burst of joy that settles into content satisfaction
5. Straight Increase/Decrease: Sudden, dramatic change in emotions
   Example: An unexpected tragedy causing immediate shift from +5 to -8
6. S-Curve Increase/Decrease: Change follows an 'S' shape (slow-fast-slow)
   Example: Gradually accepting good news, rapid excitement, then settling into happiness
7. Linear Flat: No change in emotions
   Example: Maintaining determined focus throughout a challenging task

## Analysis Guidelines

### Analysis Steps:
1. Understand {protagonist}'s starting position in the story.
   - Identify their initial circumstances and relationships
   - Look for early indicators of their emotional state
   - Note their primary motivations and desires
2. Segment the story into components based on major changes in {protagonist}'s emotions.
   - The number of components should be determined by the natural transitions in their emotional state
   - Most stories will naturally fall into 4-8 components, though shorter or longer stories may fall outside this range
   - Each significant change in their emotional state should mark the start of a new component
   - As a general guideline, major emotional changes typically involve shifts of at least 3-4 points on the -10 to +10 scale
   - Components can vary in length based on the pace of emotional change
   - Avoid over-segmentation: only create new components for meaningful shifts in emotional state
3. Identify the emotional scores of each story component.
   - Scores must be whole numbers between -10 and +10 that reflect {protagonist}'s emotional state as evidenced in the story summary
   - Score changes must match the selected arc type
4. For each story component:
   - Identify the portion of the story summary that shows {protagonist}'s experience
   - Focus on events and details that reveal their emotional state
   - Note their actions, reactions, and key interactions
   - Use these details to write a description that centers on their journey
5. Identify the emotional arcs which connect story components.

After your analysis, provide the final output in the following JSON format:

{{{{
    "title": "Story Title",
    "protagonist": "Protagonist",
    "story_components": [
        {{{{
            "end_time": 0,
            "description": "#N/A",
            "end_emotional_score": initial_score,
            "arc": "#N/A"
        }}}},
        {{{{
            "end_time": percentage,
            "description": "Detailed description of events in this component",
            "end_emotional_score": score,
            "arc": "Arc Type"
        }}}},
    ]
}}}}

### Story Component Description Guidelines:
- Each description must be derived directly from the provided story summary
- Center the description on {protagonist}'s experience and perspective
- Describe events primarily in terms of their impact on {protagonist}
- Include their actions, reactions, and emotional responses
- Detail settings as they relate to their experience
- Include other characters mainly through their interaction with or impact on {protagonist}
- Quote or closely paraphrase passages that reveal their emotional state
- Include sensory details that contribute to understanding their experience

### Initial Emotional Score Guidelines:
- Carefully examine how {protagonist} is first presented in the story
- Look for descriptive words indicating their initial emotional state
- Consider their starting circumstances and relationships

## Important Notes:
- The first component always has an end_time of 0, no description, and no arc.
- Ensure that end_emotional_scores are consistent with the arc types (e.g., an "Increase" arc should have a higher end_emotional_score than the previous component).
- Emotional scores must be whole numbers between -10 and +10.
- Adjacent components should not have the same emotional score unless using Linear Flat arc.
- End times must be in ascending order and the final component must end at 100.
- Each arc type must match the emotional change described:
  * Increase arcs must show higher end scores than start scores
  * Decrease arcs must show lower end scores than start scores
  * Flat arcs must maintain the same score
- Double-check your analysis for accuracy and internal consistency before providing the final JSON output.

Please proceed with your analysis and provide the JSON output. ONLY respond with the JSON and nothing else.

____________________

EXAMPLE:

<example>
<author_name>
Charles Perrault
</author_name>
<story_title>
Cinderella at the Ball
</story_title>
<protagonist>
Cinderella
</protagonist>
<story_summary>
Heartbroken and exhausted, Cinderella toils endlessly in her own home after her father’s death leaves her at the mercy of her cruel stepmother and spiteful stepsisters. Forced to cook, clean, and tend to every chore while enduring their constant insults, Cinderella clings to a quiet hope for a kinder future, though she often feels lonely and powerless. One day, an announcement arrives that the royal family is hosting a grand ball to find a bride for the Prince. Eager for a chance at happiness, Cinderella timidly asks if she may attend. Her stepmother and stepsisters mock her wish and forbid it, leaving her devastated. Even so, Cinderella manages to gather scraps of optimism, trying to sew a suitable dress from her late mother’s belongings—only for her stepsisters to shred it in a fit of jealousy moments before the ball. Crushed by this cruel betrayal, she flees to the garden, overwhelmed by despair. It is there that her Fairy Godmother appears, transforming Cinderella’s tattered clothes into a resplendent gown and conjuring a gleaming carriage from a humble pumpkin. As Cinderella’s hopes rise, the Fairy Godmother warns her that the magic will end at midnight. At the grand royal ball, the Prince is immediately enchanted by her gentle grace and luminous presence. For the first time, Cinderella basks in admiration instead of scorn, feeling her spirits soar with each dance and conversation. However, as the clock strikes midnight, she is forced to flee the palace. In her panic to escape before the spell breaks, she loses one of her delicate glass slippers on the palace steps. Despite her sudden disappearance, the Prince is determined to find this mysterious young woman, traveling throughout the kingdom with the slipper in hand. When his search brings him to Cinderella’s home, her stepsisters deride the idea that she could be the one who captured the Prince’s heart. Yet, as soon as Cinderella tries on the slipper, it fits perfectly. Freed at last from servitude, she marries the Prince, and her enduring kindness and patience are joyously rewarded.
</story_summary>
<ideal_output>
{{{{
    "title": "Cinderella at the Ball",
    "protagonist": "Cinderella",
    "story_components": [
        {{{{
            "end_time": 0,
            "description": "#N/A",
            "end_emotional_score": -5,
            "arc": "#N/A"
        }}}},
        {{{{
            "end_time": 30,
            "description": "Cinderella weeps alone in the garden, heartbroken after her stepfamily mocks her desires and denies her chance to attend the ball. Her despair turns to wonder when her Fairy Godmother appears, transforming her circumstances through magical gifts: her pumpkin becomes a splendid carriage, mice become horses, and she receives a resplendent gown with glass slippers. Despite her rising hopes, she must bear the weight of the midnight deadline.",
            "end_emotional_score": 2,
            "arc": "Step-by-Step Increase"
        }}}},
        {{{{
            "end_time": 60,
            "description": "Cinderella experiences a profound transformation as she arrives at the grand ball. Her kindness and radiant beauty draw the Prince's attention, and she finds herself, for the first time, being treated with admiration and respect. As she dances with the Prince throughout the evening, each moment fills her with increasing joy and wonder, allowing her to momentarily forget her life of servitude.",
            "end_emotional_score": 8,
            "arc": "Gradual-to-Rapid Increase"
        }}}},
        {{{{
            "end_time": 75,
            "description": "Cinderella's magical evening shatters as the clock strikes midnight. Panic overtakes her as she flees the palace, losing a glass slipper in her desperate rush to escape. Her brief taste of happiness ends abruptly as she races to prevent the revelation of her true identity, watching her transformed world revert to its ordinary state.",
            "end_emotional_score": -3,
            "arc": "Straight Decrease"
        }}}},
        {{{{
            "end_time": 100,
            "description": "Cinderella's hopes revive when the Prince begins searching for her with the glass slipper. Her moment of triumph arrives when she steps forward in her home to try on the slipper, and it fits perfectly. Her patient endurance is finally rewarded as she marries the Prince, rising from her life of servitude to find happiness, maintaining her gracious nature by forgiving her stepfamily.",
            "end_emotional_score": 10,
            "arc": "Gradual-to-Rapid Increase"
        }}}}
    ]
}}}}
</ideal_output>
</example>

Note About Example Output:
The descriptions in the example output demonstrate the minimum expected level of detail for story components. Each description should:
- Center on the protagonist's experience and emotional journey
- Include concrete details that reveal the protagonist's state of mind
- Use language that reflects the protagonist's perspective
- Capture interactions primarily through their impact on the protagonist

"""
    
    prompt = PromptTemplate(
        input_variables=["author_name", "story_title", "protagonist", "story_summary"],  # Define the expected inputs
        template=prompt_template
    )


    config = load_config(config_path=config_path)
    llm = get_llm(llm_provider, llm_model, config, max_tokens=8192)

    # Instead of building an LLMChain, use the pipe operator:
    runnable = prompt | llm

    try:
        output = runnable.invoke({
            "author_name": author_name,
            "story_title": story_title,
            "protagonist": protagonist,
            "story_summary": story_summary,
        })
        # If output is a AIMessage, its `response_metadata` might have info
        if hasattr(output, "response_metadata"):
            print("LLM Response Metadata:", output.response_metadata)

    except Exception as e:
        print(f"Error during LLM call: {e}")
        if hasattr(e, 'response') and hasattr(e.response, 'prompt_feedback'): # Example for some libraries
            print("Prompt Feedback:", e.response.prompt_feedback)

    # If the output is an object with a 'content' attribute, extract it.
    if hasattr(output, "content"):
        output_text = output.content
    else:
        output_text = output

    #attempt to extact json (if needed)
    output_text = extract_json(output_text)


    return output_text



def validate_story_arcs(data): #data should be json object
    
    # Initialize an empty list to store validation results
    validation_results = []
    
    # Previous emotional score for comparison; start with the first component
    title = data['title']
    prev_score = data['story_components'][0]['end_emotional_score']
    
    # Iterate through story components, starting from the second one
    for component in data['story_components'][1:]:
        current_score = component['end_emotional_score']
        arc = component['arc']
        end_time = component['end_time']
        expected_change = None
        
        # Determine expected change based on the arc description
        if "Increase" in arc:
            expected_change = "increase"
        elif "Decrease" in arc:
            expected_change = "decrease"
        elif "Flat" in arc:
            expected_change = "flat"
        
        # Determine actual change
        actual_change = None
        if current_score > prev_score:
            actual_change = "increase"
        elif current_score < prev_score:
            actual_change = "decrease"
        else:
            actual_change = "flat"
        
        # Compare expected change with actual change
        matches_description = expected_change == actual_change
        
        if(matches_description == False):
            error_string = f'ERROR: In {title} at end_time: {end_time} arc specified was: {expected_change} but actual score change was: {actual_change}'
            print(error_string)
            return "invalid"
        
        # Update previous score for the next iteration
        prev_score = current_score
    
    return "valid"


def num_tokens_from_string(string: str, model: str) -> int:
    """Returns the number of tokens in a text string."""
    #encoding = tiktoken.get_encoding(encoding_name)
    encoding = tiktoken.encoding_for_model(model)
    num_tokens = len(encoding.encode(string))
    return num_tokens


# need to revise --> want to combine all summaries in one master summary
def get_story_summary(story_summary_path):

    """
    Inputs are a file path that contains story summary(s) and returns story summary
    """

    with open(story_summary_path, 'r', encoding='utf-8') as file:
        story_summary_data = json.load(file)

     # List is in priority order
    summary_sources = [
        'sparknotes', 'cliffnotes', 'bookwolf', 'gradesaver', 
        'novelguide', 'pinkmonkey', 'shmoop', 'thebestnotes', 'wiki', 'other'
    ]

    story_summary = ""
    story_summary_source = ""

    #use longest summary proxy for most complete
    for summary_source in summary_sources:
        if summary_source in story_summary_data:
            summary_text = story_summary_data[summary_source].get('summary', '')
            if summary_text and len(summary_text) > len(story_summary):
                story_summary = summary_text
                story_summary_source = summary_source
    
    return story_summary


def get_story_components(story_summary = "", author="", year="", protagonist="", output_path="", 
                      llm_provider="anthropic", llm_model="claude-3-5-sonnet-20241022"):


    summary_file_path = os.path.join(summary_dir, summary_file)
    with open(summary_file_path, 'r', encoding='utf-8') as file:
        story_data = json.load(file)
    
    
    story_title = story_data['title']
    print("Creating story data for ", story_title)

    if author == "":
        author = story_data['openlib']['author_name'][0]
    
    if year == "":
        year = story_data['openlib']['publishing']['first_publish_year']

    # List is in priority order
    summary_sources = [
        'sparknotes', 'cliffnotes', 'bookwolf', 'gradesaver', 
        'novelguide', 'pinkmonkey', 'shmoop', 'thebestnotes', 'wiki', 'other'
    ]

    story_summary = ""
    story_summary_source = ""

    #use longest summary proxy for most complete
    for summary_source in summary_sources:
        if summary_source in story_data:
            summary_text = story_data[summary_source].get('summary', '')
            if summary_text and len(summary_text) > len(story_summary):
                story_summary = summary_text
                story_summary_source = summary_source
    
    #print(story_summary_source)
    story_plot_data = analyze_story(config_path=config_path, author_name=author, story_title=story_title, protagonist=protagonist, story_summary=story_summary,
                                    llm_provider=llm_provider,llm_model=llm_model)
    story_plot_data = json.loads(story_plot_data)
    story_validity = validate_story_arcs(story_plot_data)
    story_plot_data["type"] = "book"
    story_plot_data["author"] = author
    story_plot_data["year"] = year
    story_plot_data['summary'] = story_summary
    story_plot_data['story_summary_source'] = story_summary_source
    story_plot_data['shape_validity'] = story_validity
    story_plot_data['story_data_llm'] = llm_model

    if story_plot_data['protagonist'] != protagonist:
        print("LLM designated protagonist as: ", story_plot_data['protagonist'], " but I specified protagonist as: ", protagonist)
        print("PLEASE RESOLVE")
        raise ValueError
   

    for component in story_plot_data["story_components"]:
        component['modified_end_time'] = component['end_time']
        component['modified_end_emotional_score'] = component['end_emotional_score']
    
    output_path = output_path
    title = story_plot_data['title'].lower().replace(' ', '-') + "_" + story_plot_data['protagonist'].lower().replace(' ', '-')
    output_path = os.path.join(output_path, f"{title}.json")
    with open(output_path, 'w') as json_file:
        json.dump(story_plot_data, json_file, indent=4)

    return story_plot_data, output_path











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

    #get input parameters from sheet
    story_type          = row.get('story_type')
    story_title	        = row.get('story_title')    
    story_author	    = row.get('story_author')
    story_protagonist	= row.get('story_protagonist')
    story_year	        = row.get('story_year')
    story_summary_path  = row.get('story_summary_path')




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

    # get story components
    story_components = get_story_components(
        story_summary = story_summary,
        author=story_author,
        year=story_year,
        protagonist=story_protagonist,
        llm_provider="anthropic", 
        llm_model="claude-3-5-sonnet-20241022"
    )
    
    
    
    else:
        print("Creating Story Data")
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




    # STORY STYLE / DESIGN
    story_style = get_story_style(
        config_path = PATHS['config'],
        story_title = story_title, 
        author = story_author,
        protagonist = story_protagonist, 
        llm_provider = "anthropic", #"google", #"openai",#, #"openai",, #"anthropic", #google", 
        llm_model = "claude-3-5-sonnet-latest"#"gemini-2.5-pro-preview-06-05", #o3-mini-2025-01-31", #"o4-mini-2025-04-16" #"gemini-2.5-pro-preview-05-06" #"o3-2025-04-16" #"gemini-2.5-pro-preview-05-06"#o3-2025-04-16"#"gemini-2.5-pro-preview-05-06" #"claude-3-5-sonnet-latest" #"gemini-2.5-pro-preview-03-25"
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
        border_thickness = 150 #this is in pixels with DPI = 300 so 150 --> 0.5 in
        width_in_inches = 8
        height_in_inches = 10
        wrap_in_inches = 0
        max_num_steps = 2
        step_k = 6
        #has_border = False
        has_border = True
        fixed_margin_in_inches = 0.6 #this is suppose to be where text ends
        #so difference between fixed_margin_in_inches - (border_thickness/300) = space between text and white border

    elif product == "print" and size == "11x14":

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

        line_thickness = 38
        font_size = 12
        gap_above_title = 102 #value was 26
        top_text = author + ", " + str(year)
        top_text_font_size = 12
        bottom_text_font_size = 12
        top_and_bottom_text_band = 1
        border_thickness = 360 #600 #300 #360 ## --> (360/300)/2 DPI --> 0.6 inches OR (300/300 DPI)/2 --> 0.5 in 
        width_in_inches = 11
        height_in_inches = 14
        wrap_in_inches = 0
        max_num_steps = 2
        step_k = 6
        has_border = True
        fixed_margin_in_inches = 0.85  #1.25 #0.75 #0.85 
        #1 = 0.6 + 0.4 = 1
        #0.85 ## --> border thickness (0.6) + 0.25 = 0.85

        #note that:
        #border thickness is in pixels and apparently half of it gets clipped (idk why) so with 300 DPI --> (150/300) --> 0.25
        #fixed_margin_in_inches is space between edge of print and where text begins
        #space between white edge and text is fixed_margin_in_inches -(border_thickness/300)
        #so if we want ~0.25in between white border and text AND a 0.6 in white border that means
        #border thickness = 

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