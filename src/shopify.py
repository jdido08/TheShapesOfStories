import requests
import json
import base64
import os
import yaml

# --- Function to GET all images for a product ---
def get_shopify_product_images(shop_url, api_token, product_id):
    """Fetches a list of all images for a specific Shopify product."""
    api_version = "2024-07"
    url = f"https://{shop_url}/admin/api/{api_version}/products/{product_id}/images.json"
    headers = {"X-Shopify-Access-Token": api_token}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("images", [])
    print(f"Error fetching Shopify images: {response.status_code} - {response.text}")
    return []

# --- Function to DELETE an image from a product ---
def delete_shopify_image(shop_url, api_token, product_id, image_id):
    """Deletes a specific image from a Shopify product."""
    print(f"🗑️ Deleting Shopify image ID: {image_id}...")
    api_version = "2024-07"
    url = f"https://{shop_url}/admin/api/{api_version}/products/{product_id}/images/{image_id}.json"
    headers = {"X-Shopify-Access-Token": api_token}
    
    response = requests.delete(url, headers=headers)
    
    if response.status_code == 200:
        print(f"✅ Image {image_id} deleted successfully.")
        return True
    print(f"❌ Failed to delete image {image_id}: {response.status_code} - {response.text}")
    return False

# --- Function to UPLOAD a new image from a local file ---
def upload_shopify_image_from_file(shop_url, api_token, product_id, file_path):
    """Uploads a new product image to Shopify from a local file."""
    print(f"🚀 Uploading image from: {file_path}...")
    
    # 1. Read the image file in binary mode and encode it in base64
    try:
        with open(file_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    except FileNotFoundError:
        print(f"❌ Error: File not found at {file_path}")
        return None
        
    # 2. Prepare the API request
    api_version = "2024-07"
    url = f"https://{shop_url}/admin/api/{api_version}/products/{product_id}/images.json"
    headers = {"X-Shopify-Access-Token": api_token, "Content-Type": "application/json"}
    
    payload = {
        "image": {
            "attachment": encoded_string,
            "filename": os.path.basename(file_path)
        }
    }
    
    # 3. Send the POST request
    response = requests.post(url, headers=headers, data=json.dumps(payload))
    
    if response.status_code == 201: # 201 Created is the success code here
        print(f"✅ Image '{os.path.basename(file_path)}' uploaded successfully.")
        return response.json()
    
    print(f"❌ Failed to upload image: {response.status_code} - {response.text}")
    return None

def load_credentials_from_yaml(item):
    with open("/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml", "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config[item]




# --- YOUR SHOPIFY CREDENTIALS ---
SHOPIFY_URL = "fnjm07-qy.myshopify.com"
SHOPIFY_API_TOKEN = load_credentials_from_yaml("shopify_key")

# Assume you got this from the Printify publish step
shopify_product_id = "7961503203402" 

# --- 1. Clear out the default Printify mockups ---
print(f"--- Managing images for Shopify Product ID: {shopify_product_id} ---")
existing_images = get_shopify_product_images(SHOPIFY_URL, SHOPIFY_API_TOKEN, shopify_product_id)

if existing_images:
    print(f"Found {len(existing_images)} existing images. Deleting them now.")
    for image in existing_images:
        delete_shopify_image(SHOPIFY_URL, SHOPIFY_API_TOKEN, shopify_product_id, image['id'])
else:
    print("No existing images found or an error occurred.")

# --- 2. Upload your own desired mockups from local files ---
# Create a list of the file paths for the mockups you want to upload
# Make sure these files exist on your computer.
mockup_files_to_upload = [
    '/Users/johnmikedidonato/Projects/TheShapesOfStories/final_mockup_test.jpg',
]

print(f"\nUploading {len(mockup_files_to_upload)} new mockups...")
for file_path in mockup_files_to_upload:
    upload_shopify_image_from_file(SHOPIFY_URL, SHOPIFY_API_TOKEN, shopify_product_id, file_path)
    
print("\n--- Image update process complete! ---")