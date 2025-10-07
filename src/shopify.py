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
    print(f"❌ Error fetching Shopify images: {response.status_code} - {response.text}")
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

def load_credentials_from_yaml(item, config_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml"):
    with open(config_path, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config[item]




def edit_shopify_product_listing(product_data_path, config_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml"):
    # --- YOUR SHOPIFY CREDENTIALS ---
    SHOPIFY_URL = "fnjm07-qy.myshopify.com" #maybe put this in YAML?
    SHOPIFY_API_TOKEN = load_credentials_from_yaml("shopify_key")

    #open product data to get product shopify id 
    with open(product_data_path, 'r') as f:  #open product json data that was just created
        product_data = json.load(f)
    
    #get important details about the product: title, author, protagonist, year, description, story slug, product slug , product_size, product_type, product_design_path 
    
        #get important details about the product: title, author, protagonist, year, description, story slug, product slug , product_size, product_type, product_design_path 
    title = product_data['title']
    protagonist = product_data['protagonist']
    product_type = product_data['product_type']
    product_size = product_data['product_size']
    shopify_product_id = product_data['shopify_product_id']
    mockup_paths = product_data['mockup_paths']

    print("Editing ", title, "-", protagonist, "-", product_type, "-", product_size, " on SHOPIFY")



    #GET AND DELETE EXISTING IMAGES ON SHOPIFY BEFORE UPLOADING MOCKUPS
    existing_images = get_shopify_product_images(SHOPIFY_URL, SHOPIFY_API_TOKEN, shopify_product_id)
    if existing_images:
        print(f"Found {len(existing_images)} existing images. Deleting them now.")
        for image in existing_images:
            delete_shopify_image(SHOPIFY_URL, SHOPIFY_API_TOKEN, shopify_product_id, image['id'])
        print("✅ EXISTING SHOPIFY MOCKUPS UPDATED")
    else:
        print("No existing images found or an error occurred.")

        
    #UPLOAD MOCKUPS TO SHOPIFY LISTING 
    for file_path in mockup_paths:
        upload_shopify_image_from_file(SHOPIFY_URL, SHOPIFY_API_TOKEN, shopify_product_id, file_path)
    print("✅ SHOPIFY MOCKUPS UPDATED")



#edit_shopify_product_listing(product_data_path="/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/product_data/romeo-and-juliet-juliet-print-11x14-purple-gold.json")


## TROUBLESHOOTING FUNCTUION
def debug_get_product(shop_url, api_token, product_id):
    api_version = "2024-07"
    url = f"https://{shop_url}/admin/api/{api_version}/products/{product_id}.json"
    headers = {"X-Shopify-Access-Token": api_token}
    r = requests.get(url, headers=headers)
    print("Status:", r.status_code)
    print("Body:", r.text[:600])  # peek
    return r


def debug_shop(shop_url, token):
    url = f"https://{shop_url}/admin/api/2024-07/shop.json"
    r = requests.get(url, headers={"X-Shopify-Access-Token": token})
    print("shop:", r.status_code, r.text[:300])

def debug_list_products(shop_url, token):
    url = f"https://{shop_url}/admin/api/2024-07/products.json?limit=5&fields=id,title,status"
    r = requests.get(url, headers={"X-Shopify-Access-Token": token})
    print("list:", r.status_code, r.text[:600])


# run once
SHOPIFY_URL = "fnjm07-qy.myshopify.com" #maybe put this in YAML?
SHOPIFY_API_TOKEN = load_credentials_from_yaml("shopify_key")
#debug_get_product("fnjm07-qy.myshopify.com", SHOPIFY_API_TOKEN, "8029552181322")
#debug_shop("fnjm07-qy.myshopify.com", SHOPIFY_API_TOKEN)
debug_list_products("fnjm07-qy.myshopify.com", SHOPIFY_API_TOKEN)
