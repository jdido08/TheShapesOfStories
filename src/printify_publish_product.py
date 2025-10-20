import requests
import json
import yaml
import requests
import json
import yaml
import sys
from google.oauth2.service_account import Credentials
import gspread
from googleapiclient.discovery import build
from datetime import datetime
import time
import os
import base64

## FROM printify_print_details.py ##
# ✅ Blueprint: Matte Vertical Posters -> 282
# - Provider option: Printify Choice (id 99)
# - Provider option: Sensaria (id 2)
# ✅ Provider: Printify Choice -> 99
# ✅ Variant: id=43135 title=11″ x 14″ / Matte size=11″ x 14″ paper=Matte
#    Placeholder: 3300x4200 (position front)
printify_print_details = {
    "print-11x14":{
        "blueprint_id":282,
        "provider_id":99,
        "variant_id":43135,
        "price":2499,
        "width_dimensions":3300,
        "height_dimensions":4200
    }
}               

SHOP_ID = 23014386
SHOP_TITLE = "The Shapes of Stories"
SHOP_SALES_CHANNEL = "shopify"


from PIL import Image
def ensure_dimensions(image_path, w=3300, h=4200):
    with Image.open(image_path) as im:
        if im.size != (w, h):
            print("❌ Design Dimensions Bad. Design is: ", im.size, " & expecting ", w, "x", h)
            return "image_dimensions_bad"
        else:
            print("✅ Design Dimensions Good")
            return "image_dimensions_good"


def upload_image(api_token, image_path):
    """Uploads an image to Printify using Base64 encoding and returns its ID."""
    #print("Uploading image using Base64 method...")
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
            #print(json.dumps(image_data, indent=4))
            return image_id
        else:
            print(f"❌ Error uploading image: {response.status_code}")
            print(f"Response: {response.text}")
            return None
            
    except FileNotFoundError:
        print(f"❌ Error: The file was not found at path: {image_path}")
        return None


def get_printify_creds_from_yaml(file_path):
    """Loads API key from a YAML file."""
    with open(file_path, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config["printify_key"]


def create_product(api_token, shop_id, product_data):
    """Builds the JSON payload and creates the final product."""
    #print("FINAL STEP: Creating product...")
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
        print("✅ PRODUCT CREATED ON PRINTIFY")
        created_product_data = response.json()
        #print(json.dumps(created_product_data, indent=2))
        return created_product_data  # <-- The essential fix is here
    else:
        print("❌ FINAL ERROR: Failed to create product.")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return None # <-- Return None on failure


def get_product_details(api_token, shop_id, product_id):
    """
    Fetches the complete data for a single product from a shop.

    This function is used to retrieve the final product information, including the
    Shopify ID and variant SKUs, after the publishing process is complete.
    """
    #print(f"Fetching final details for product ID: {product_id}...")
    
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
        #print("✅ Success! Retrieved final product data.")
        return product_data
    else:
        print(f"❌ Error fetching product details: {response.status_code}")
        print(f"Response: {response.text}")
        return None


def publish_product(api_token, shop_id, product_id):
    """Publishes a product and controls which mockups are visible."""
    #print("STEP 6: Publishing product with selected mockups...")
    url = f"https://api.printify.com/v1/shops/{shop_id}/products/{product_id}/publish.json"
    headers = {"Authorization": f"Bearer {api_token}", "Content-Type": "application/json"}

    # This payload controls what gets published.
    # We are including the "images" key to control the mockup selection.
    payload = {
        "title": True,
        "description": True,
        "variants": True,
        "images": False, # Pass the list of mockups here
        "tags": False
    }

    response = requests.post(url, headers=headers, json=payload)

    if 200 <= response.status_code < 300:
        print("✅ PRODUCT PUBLISHED ON PRINTIFY")
        created_product_data = response.json()
        #print(json.dumps(created_product_data, indent=2))
        return True  # <-- This returns the data
    else:
        print("❌ FINAL ERROR: Failed to create product.")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        return False # <-- This handles the failure case


def publish_product_on_printify(product_data_path, config_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml"):

    PRINTIFY_API_KEY = get_printify_creds_from_yaml(config_path)

    #open product data path 
    with open(product_data_path, 'r') as f:  #open product json data that was just created
        product_data = json.load(f)
    
    #get important details about the product: title, author, protagonist, year, description, story slug, product slug , product_size, product_type, product_design_path 
    title = product_data['product_slug'] #making title the product slug which is unique per product variant
    protagonist = product_data['protagonist']
    description = product_data['product_description_html']
    product_type = product_data['product_type']
    product_size = product_data['product_size']
    product_design_path = product_data['product_design_path']

    #print
    print("Publishing ", title, "-", protagonist, "-", product_type, "-", product_size, " on PRINTIFY")

    #set printify product type details --> see printify_print_details.py
    if product_type == "print" and product_size == "11x14":
        blueprint_id = printify_print_details[product_type + "-" + product_size]["blueprint_id"]
        provider_id = printify_print_details[product_type + "-" + product_size]["provider_id"]
        variant_id = printify_print_details[product_type + "-" + product_size]["variant_id"]
        price = printify_print_details[product_type + "-" + product_size]["price"]
        width_dimensions = printify_print_details[product_type + "-" + product_size]["width_dimensions"]
        height_dimensions = printify_print_details[product_type + "-" + product_size]["height_dimensions"]
    else:
        print("❌ ERROR: Only print 11x14 supported today")
        return

    #before creating printify product -- make sure design matches product dimenions 
    image_dimensions_quality = ensure_dimensions(product_design_path, w=width_dimensions, h=height_dimensions)
    if image_dimensions_quality == "image_dimensions_bad":
        return 
    
    #upload design to printify
    product_image_id = upload_image(PRINTIFY_API_KEY, product_design_path)
    if not product_image_id:
        raise RuntimeError("❌ Design Image upload failed")
    
    #assemble product details
    product_details = {
            "title": title,
            "description": description,
            "blueprint_id": blueprint_id, #"Matte Vertical Posters"
            "provider_id": provider_id, #printify choice 
            "variant_id": variant_id, #matt 8x10
            "price": price, #in cents 
            "image_id": product_image_id
        }

    #CREATE PRODUCT ON PRINTIFY
    created = create_product(PRINTIFY_API_KEY, SHOP_ID, product_details)
    if not created:
        raise RuntimeError("Create product failed")
    printify_product_id = created["id"]


    # publish without images (no mockups to Shopify)
    # published = publish_product(PRINTIFY_API_KEY, SHOP_ID, printify_product_id)  # make sure images=False inside
    # if not published:
    #     raise RuntimeError("Publish failed")
    

    # light poll for Shopify id
    shopify_product_id = None
    # for _ in range(6):
    #     data = get_product_details(PRINTIFY_API_KEY, SHOP_ID, printify_product_id)
    #     shopify_product_id = data.get("external", {}).get("id")
    #     if shopify_product_id:
    #         print("✅ Success! Retrieved shopify_product_id.")
    #         break
    #     time.sleep(5)
    # if shopify_product_id == None:
    #     print("\n❌ Failed to Retrieve shopify_product_id")
    

    # pick an enabled SKU for your sheet
    sku = ""
    for v in created.get("variants", []):
        if v.get("is_enabled"):
            sku = v.get("sku"); break


    #save + other things printify_product_id, shopify_product_id, sku -- back to product data 
    product_data["printify_blueprint_id"] = blueprint_id
    product_data["printify_provider_id"] = provider_id
    product_data["printify_variant_id"] = variant_id
    product_data["printify_product_id"] = printify_product_id
    product_data["printify_price"] = price
    product_data["printify_product_image_id"] = product_image_id
    product_data["shopify_product_id"] = shopify_product_id
    product_data["sku"] = sku

    with open(product_data_path, "w", encoding="utf-8") as f:     # save it back to the same file
        json.dump(product_data, f, ensure_ascii=False, indent=2)
        f.write("\n")  # optional newline at EOF
    time.sleep(2)
    print("✅ Product Created and Published on Printify")

    #open story data and link created SKU to specific product 
    story_data_path = product_data['story_data_path']
    product_type = product_data['product_type']
    product_slug = product_data['product_slug']
    with open(story_data_path, 'r') as f:
        story_data = json.load(f)
    #write sku to product data 
    story_data['products'][product_type][product_slug]['sku'] = sku

    with open(story_data_path, "w", encoding="utf-8") as f:     # save it back to the same file
        json.dump(story_data, f, ensure_ascii=False, indent=2)
        f.write("\n")  # optional newline at EOF
    time.sleep(1)
    print("✅ Story Data Updated w/ Product Variant SKU")

    return 


   
# publish_product_on_printify("/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/product_data/the-stranger-meursault-print-11x14-helvetica-neue-white-gray.json")