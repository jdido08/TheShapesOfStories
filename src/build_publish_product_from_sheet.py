from paths import PATHS
from create_story_data               import create_story_data
from create_product_data             import create_product_data
from printify_publish_product        import publish_product_on_printify
from shopify_create_product          import create_shopify_product
from shopify_create_product_variant  import create_shopify_product_variant
from shopify_product_variant_mockups import add_shopify_product_variant_mockups

import yaml
import os
import sys
import gspread
from google.oauth2.service_account import Credentials
import json


def publish_product(product_data_path):

    with open(product_data_path, "r", encoding="utf-8") as f:
        product_data = json.load(f)
    story_data_path = product_data['story_data_path']

    publish_product_on_printify(product_data_path=product_data_path)

    create_shopify_product(story_data_path, "print")

    create_shopify_product_variant(story_data_path, product_type="print", product_slug="ALL", delete_placeholder_variants=True)

    add_shopify_product_variant_mockups(product_data_path)




# Load credentials from the YAML file
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


#link https://docs.google.com/spreadsheets/d/16tmqmaXRN_a_TV4iWdkHkJb4XPgc7dKKZZzd7dVtQs4/edit?usp=sharing
sheet_id = "16tmqmaXRN_a_TV4iWdkHkJb4XPgc7dKKZZzd7dVtQs4"
spreadsheet = client.open_by_key(sheet_id)
worksheet = spreadsheet.worksheet("Publish Product")


# Get all rows from the sheet
rows = worksheet.get_all_records()
for row in rows:
    
    #get input data
    product_data_path = row.get("product_data_path")

    if product_data_path == "":
        print("Skipping row. Missing required fields")
        continue

    publish_product(
       product_data_path = product_data_path
    )


