# import requests
# import json
# import yaml

# shop_id = 23014386,
# shop_title = "The Shapes of Stories"
# shop_sales_channel = "shopify"
# blueprint_id: 282 #"Matte Vertical Posters"
# print_provider_id: 99 #Printify Choice
#providers:
# Found '{'id': 99, 'title': 'Printify Choice'}' with print_provider_id: 99
# Found '{'id': 2, 'title': 'Sensaria'}' with print_provider_id: 2
#variant
#{'id': 114557, 'title': '8" x 10" / Matte', 'options': {'size': '8" x 10"', 'paper': 'Matte'}, 'placeholders': [{'position': 'front', 'width': 2400, 'height': 3000}], 'decoration_methods': ['digital-printing']}


import requests
import json
import yaml
import sys
from google.oauth2.service_account import Credentials
import gspread
from googleapiclient.discovery import build
from datetime import datetime
import time


# --- Your Existing Code (Slightly Modified for Clarity) ---

def load_credentials_from_yaml(file_path):
    """Loads API key from a YAML file."""
    with open(file_path, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config["printify_key"]

# --- New Functions to Get Product IDs ---

def get_blueprints(api_token, target_product):
    """Fetches all available blueprints (products) from the Printify catalog."""
    print("STEP 1: Fetching blueprints (products)...")
    url = "https://api.printify.com/v1/catalog/blueprints.json"
    headers = {"Authorization": f"Bearer {api_token}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        blueprints = response.json()
        print(f"✅ Success! Found {len(blueprints)} blueprints.\n")
        
        # --- Example: Find and return the ID for a specific T-Shirt ---

        for blueprint in blueprints:
            if blueprint['title'] == target_product:
                print(f"Found '{target_product}' with blueprint_id: {blueprint['id']}")
                return blueprint['id']
        print(f"Could not find blueprint for '{target_product}'.")
        return None
    else:
        print(f"❌ Error fetching blueprints: {response.status_code}")
        return None

def get_print_providers(api_token, blueprint_id):
    """Fetches all print providers for a specific blueprint."""
    print("\nSTEP 2: Fetching print providers for the selected blueprint...")
    url = f"https://api.printify.com/v1/catalog/blueprints/{blueprint_id}/print_providers.json"
    headers = {"Authorization": f"Bearer {api_token}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        providers = response.json()
        print(f"✅ Success! Found {len(providers)} print providers.\n")

        # --- Example: Find and return the ID for a specific provider ---
        #target_provider = "Monster Digital" 
        for provider in providers:
            print(f"Found '{provider}' with print_provider_id: {provider['id']}")
            # if provider['title'] == target_provider:
            #     print(f"Found '{target_provider}' with print_provider_id: {provider['id']}")
            #     return provider['id']
        #print(f"Could not find print provider '{target_provider}'. Returning the first available.")
        return providers[0]['id'] if providers else None
    else:
        print(f"❌ Error fetching print providers: {response.status_code}")
        return None

def get_variants(api_token, blueprint_id, print_provider_id):
    """Fetches all variants (e.g., sizes, colors) for a product from a specific provider."""
    print("\nSTEP 3: Fetching variants from the selected provider...")
    url = f"https://api.printify.com/v1/catalog/blueprints/{blueprint_id}/print_providers/{print_provider_id}/variants.json"
    headers = {"Authorization": f"Bearer {api_token}"}

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        variants = data.get('variants', [])
        print(f"✅ Success! Found {len(variants)} variants.\n")
        
        # --- Example: Print and return all variant IDs ---
        variant_ids = []
        print("Available variants (ID, Title, Price):")
        for variant in variants:
            print(variant)
            # variant_id = variant['id']
            # title = variant['title']
            # price = variant['price'] / 100 # Price is in cents
            # variant_ids.append(variant_id)
            # print(f"- ID: {variant_id}, Title: {title}, Price: ${price:.2f}")

        return variant_ids
    else:
        print(f"❌ Error fetching variants: {response.status_code}")
        return []
    
def get_shop_id(api_token):
        
    # The API endpoint for retrieving shop information
    url = "https://api.printify.com/v1/shops.json"

    # Set up the authorization header
    headers = {
        "Authorization": f"Bearer {api_token}"
    }

    # Send the GET request to the Printify API
    response = requests.get(url, headers=headers)

    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response into a Python list
        shops = response.json()
        print("✅ Success! Found the following shops:")
        
        # Pretty-print the JSON output
        print(json.dumps(shops, indent=4))

        # You can also iterate through the shops to find a specific one
        # for shop in shops:
        #     print(f"Shop Name: {shop['title']}, Shop ID: {shop['id']}")

    else:
        print(f"❌ Error: Failed to retrieve shops. Status code: {response.status_code}")
        print(f"Response: {response.text}")


import requests
import json
import os # <-- Add this import
import base64 # <-- Add this new import

def upload_image(api_token, image_path):
    """Uploads an image to Printify using Base64 encoding and returns its ID."""
    print("Uploading image using Base64 method...")
    url = "https://api.printify.com/v1/uploads/images.json"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }

    try:
        file_name = os.path.basename(image_path)

        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        
        payload = {
            "file_name": file_name,
            "contents": encoded_string
        }
        
        response = requests.post(url, headers=headers, json=payload)

        # --- THIS IS THE CORRECTED PART ---
        if 200 <= response.status_code < 300: # Checks for any success code (200, 201, etc.)
            image_data = response.json()
            image_id = image_data.get("id")
            print("✅ Success! Image uploaded.")
            print(json.dumps(image_data, indent=4))
            return image_id
        else:
            print(f"❌ Error uploading image: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except FileNotFoundError:
        print(f"❌ Error: The file was not found at path: {image_path}")
        return None


def create_product(api_token, shop_id, product_data):
    """Builds the JSON payload and creates the final product."""
    print("FINAL STEP: Creating product...")
    url = f"https://api.printify.com/v1/shops/{shop_id}/products.json"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}
    
    # --- This is the final JSON payload for the product ---
    payload = {
        "title": product_data["title"],
        "description": product_data["description"],
        "blueprint_id": product_data["blueprint_id"],
        "print_provider_id": product_data["provider_id"],
        "variants": [{
            "id": product_data["variant_id"],
            "price": product_data["price"], # Price in cents
            "is_enabled": True
        }],
        "print_areas": [{
            "variant_ids": [product_data["variant_id"]],
            "placeholders": [{
                "position": "front",
                "images": [{
                    "id": product_data["image_id"],
                    "x": 0.5, "y": 0.5, "scale": 1, "angle": 0
                }]
            }]
        }]
    }

    response = requests.post(url, headers=headers, json=payload)

    if 200 <= response.status_code < 300:
        print("\n🎉 PRODUCT CREATED SUCCESSFULLY! 🎉")
        created_product_data = response.json()
        print(json.dumps(created_product_data, indent=2))
        return created_product_data  # <-- The essential fix is here
    else:
        print("\n❌ FINAL ERROR: Failed to create product.")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return None # <-- Return None on failure

def update_mockup_selection(api_token, shop_id, product_id, images_data):
    """Updates a product to select which mockups will be published."""
    print("Updating mockup selection...")
    url = f"https://api.printify.com/v1/shops/{shop_id}/products/{product_id}.json"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}

    # The payload only needs to contain the fields you want to change.
    payload = {
        "images": images_data
    }

    response = requests.put(url, headers=headers, json=payload)

    if 200 <= response.status_code < 300:
        print("✅ Mockup selection updated successfully.")
        return True
    else:
        print("❌ Error updating mockup selection.")
        print(f"Response: {response.text}")
        return False

def publish_product(api_token, shop_id, product_id):
    """Publishes a product and controls which mockups are visible."""
    print("STEP 6: Publishing product with selected mockups...")
    url = f"https://api.printify.com/v1/shops/{shop_id}/products/{product_id}/publish.json"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}

    # This payload controls what gets published.
    # We are including the "images" key to control the mockup selection.
    payload = {
        "title": True,
        "description": False,
        "variants": True,
        "images": True, # Pass the list of mockups here
        "tags": False
    }

    response = requests.post(url, headers=headers, json=payload)

    if 200 <= response.status_code < 300:
        print("\n🎉 PRODUCT CREATED SUCCESSFULLY! 🎉")
        created_product_data = response.json()
        print(json.dumps(created_product_data, indent=2))
        return created_product_data  # <-- This returns the data
    else:
        print("\n❌ FINAL ERROR: Failed to create product.")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return None # <-- This handles the failure case


import requests
import json

def get_product_details(api_token, shop_id, product_id):
    """
    Fetches the complete data for a single product from a shop.

    This function is used to retrieve the final product information, including the
    Shopify ID and variant SKUs, after the publishing process is complete.
    """
    print(f"Fetching final details for product ID: {product_id}...")
    
    # The API endpoint for getting a specific product's details
    url = f"https://api.printify.com/v1/shops/{shop_id}/products/{product_id}.json"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    # Make the GET request
    response = requests.get(url, headers=headers)
    
    # Check for a successful response
    if response.status_code == 200:
        product_data = response.json()
        print("✅ Success! Retrieved final product data.")
        return product_data
    else:
        print(f"❌ Error fetching product details: {response.status_code}")
        print(f"Response: {response.text}")
        return None


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



    
# Use the configured path from the PATHS dictionary
with open(PATHS['config'], "r") as yaml_file:
    config = yaml.safe_load(yaml_file)
    google_creds_data = config["google_sheets"]

# Define the correct scope
SCOPES = ["https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
]

# Create credentials with the correct scope
credentials = Credentials.from_service_account_info(google_creds_data, scopes=SCOPES)

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
sheet_id = "1V63O3KwADfTKivRVnz_YfONmWu8kmfwk_mgvu7cdGLY"
spreadsheet = client.open_by_key(sheet_id)
worksheet = spreadsheet.worksheet("To-Be Published")

CONFIG_FILE = "/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml"
printify_api_token = load_credentials_from_yaml(CONFIG_FILE)

# Get all rows from the sheet
rows = worksheet.get_all_records()

#loop through all rows but really should just be first row
for row in rows:
    product = row.get("product")
    size = row.get("size")
    line_type = row.get("line_type")
    file_format = row.get("file_format")
    title = str(row.get("title"))
    subtitle = str(row.get("subtitle"))
    author = row.get("author")
    protagonist = row.get("protagonist")
    year = row.get("year")
    design_style = row.get("design_style")
    background_color = row.get("background_color")
    font_color = row.get("font_color")
    border_color = row.get("border_color")
    font = row.get("font")
    summary_file = row.get("summary_file")
    story_data_file = row.get("story_data_file")
    story_shape_file = row.get("story_shape_file")
    local_summary_path = row.get("local_summary_path")
    local_story_data_path = row.get("local_story_data_path")
    local_story_shape_path = row.get("local_story_shape_path")

    product_details = {}
    if size == "8x10":
        #upload image to printify and get image id 
        uploaded_image_id = upload_image(printify_api_token, local_story_shape_path)

        if uploaded_image_id:
            print(f"\nSuccessfully retrieved uploaded image ID: {uploaded_image_id}")

            product_details = {
                "title": title,
                "description": "",
                "blueprint_id": 282, #"Matte Vertical Posters"
                "provider_id": 99, #printify choice 
                "variant_id": 114557, #matt 8x10
                "price": 2499, #in cents 
                "image_id": uploaded_image_id
            }

            # shop_id = 23014386,
            # shop_title = "The Shapes of Stories"
            # shop_sales_channel = "shopify"
            created_product = create_product(printify_api_token, 23014386, product_details)
            # You can now access the ID like this
            if created_product:
                time.sleep(20)
                print(created_product)
                # product_id = created_product["id"]
                # available_mockups = created_product["images"]


                # 1. Get the ID and SKU from the created_product data
                product_id = created_product["id"] # This is your Printify ID
                sku = ""
                for variant in created_product.get("variants", []):
                    if variant.get("is_enabled"):
                        sku = variant.get("sku")
                        break

                available_mockups = created_product["images"]

                # --- Step 1: Select which mockups to use ---
                for mockup in available_mockups:
                    mockup["is_selected_for_publishing"] = False
                    mockup["is_default"] = False

                if len(available_mockups) > 1:
                    available_mockups[1]["is_selected_for_publishing"] = True
                    available_mockups[1]["is_default"] = True
                    print(f"Selecting primary mockup: {available_mockups[1]['src']}")

                # --- Step 2: Update the product with your mockup selection ---
                update_successful = update_mockup_selection(
                    printify_api_token,
                    23014386,
                    product_id,
                    available_mockups
                )

                if update_successful:
                    print("Waiting 5 seconds for Printify to process the update...")
                    time.sleep(5)  # <-- Add a 5-second pause


                    # Call your existing publish_product function
                    published_product_data = publish_product(
                        printify_api_token,
                        23014386,
                        product_id
                    )  

                    print("Waiting 5 seconds for Printify to publish the product...")
                    time.sleep(10)


                    product_data = get_product_details(printify_api_token, 23014386, product_id)

                    shopify_id = None
                    if product_data.get("external"):
                        shopify_id = product_data["external"].get("id")

                    published_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
                        design_style,
                        background_color,
                        font_color,
                        border_color,
                        font,
                        summary_file,
                        story_data_file,
                        story_shape_file,
                        local_summary_path,
                        local_story_data_path,
                        local_story_shape_path,
                        product_id,
                        sku,
                        shopify_id,
                        published_at
                    ]

                    published_worksheet = spreadsheet.worksheet("Published")
                    published_worksheet.append_row(new_row_data)
                    print(f"✅ Successfully saved product {product_id} to Google Sheet.")



                
