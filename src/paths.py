# This dictionary will hold all our configured paths
import os, sys 

PATHS = {}

local_drive_path = os.path.expanduser('~/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive')
if not os.path.exists(local_drive_path): # Fallback for older Google Drive versions
    local_drive_path = '/Volumes/GoogleDrive/My Drive'

BASE_DIR = local_drive_path

# --- Define all other paths relative to the base directory ---
PATHS['src'] = os.path.join(BASE_DIR, 'src')
PATHS['summaries'] = os.path.join(BASE_DIR, 'summaries')
PATHS['story_summaries'] = os.path.join(BASE_DIR, 'story_summaries')
PATHS['story_data'] = os.path.join(BASE_DIR, 'story_data')
PATHS['product_data'] = os.path.join(BASE_DIR, 'product_data')
PATHS['product_designs'] = os.path.join(BASE_DIR, 'product_designs')
PATHS['shapes_output'] = os.path.join(BASE_DIR, 'story_shapes')
PATHS['supporting_designs'] = os.path.join(BASE_DIR, 'supporting_designs')
PATHS['product_mockups'] = os.path.join(BASE_DIR, 'product_mockups')
PATHS['story_covers'] = os.path.join(BASE_DIR, 'story_covers')
PATHS['story_distillations'] = os.path.join(BASE_DIR, 'story_distillations')
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