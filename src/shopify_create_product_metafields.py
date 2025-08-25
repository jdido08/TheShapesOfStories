
"""
shopify_metafield_definitions.py
---------------------------------
Create PRODUCT and PRODUCT_VARIANT metafield *definitions* via Shopify Admin GraphQL.
(No value setting; no product edits.)

Usage:
  pip install requests
  export SHOPIFY_SHOP="your-store.myshopify.com"
  export SHOPIFY_ADMIN_TOKEN="shpat_***"
  export SHOPIFY_API_VERSION="2025-07"   # optional, defaults to 2025-07

  # Create all definitions
  python shopify_metafield_definitions.py --create

  # (Optional) Pin a few handy fields in the Admin sidebar
  python shopify_metafield_definitions.py --pin
"""
import os, json, time, yaml
from typing import Any, Dict, List, Optional
import requests

def load_credentials_from_yaml(item):
    with open("/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml", "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config[item]


# -------------------------
# Config
# -------------------------
SHOP = load_credentials_from_yaml('shopify_url')
TOKEN = load_credentials_from_yaml('shopify_key')
API_VERSION="2025-07"

if not SHOP or not TOKEN:
    raise SystemExit("Set SHOPIFY_SHOP and SHOPIFY_ADMIN_TOKEN env vars first.")

URL = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json"
HDRS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

# ---- Choices for single-select-like fields ----
MEDIUM_CHOICES = ["print", "canvas", "t-shirt", "mug"]
LINE_TYPE_CHOICES = ["line", "text"]
ARCHETYPE_CHOICES = ["Icarus", "Man in Hole", "Cinderella", "Boy Meets Girl", "Oedipus", "Rags to Riches"]

# ---- Definitions to create ----
DEF_LIST: List[dict] = [
    # PRODUCT: story.*
    dict(name="Story Slug", namespace="story", key="slug", type="single_line_text_field", ownerType="PRODUCT",
         validations=[{"name":"regex","value":"^[a-z0-9-]+$"}]),
    dict(name="Story Title", namespace="story", key="title", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Author", namespace="story", key="author", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Character / Protagonist", namespace="story", key="character", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Series", namespace="story", key="series", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Universe", namespace="story", key="universe", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Genre", namespace="story", key="genre", type="list.single_line_text_field", ownerType="PRODUCT"),
    dict(name="Subgenre", namespace="story", key="subgenre", type="list.single_line_text_field", ownerType="PRODUCT"),
    dict(name="Publication Year", namespace="story", key="publication_year", type="number_integer", ownerType="PRODUCT"),
    dict(name="Publication Country", namespace="story", key="publication_country", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Setting Era", namespace="story", key="setting_era", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Setting Time", namespace="story", key="setting_time", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Setting City", namespace="story", key="setting_city", type="list.single_line_text_field", ownerType="PRODUCT"),
    dict(name="Setting Region", namespace="story", key="setting_region", type="list.single_line_text_field", ownerType="PRODUCT"),
    dict(name="Setting Country", namespace="story", key="setting_country", type="list.single_line_text_field", ownerType="PRODUCT"),
    dict(name="Language", namespace="story", key="language", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Awards", namespace="story", key="awards", type="list.single_line_text_field", ownerType="PRODUCT"),

    # PRODUCT: design.*
    dict(name="Medium", namespace="design", key="medium", type="single_line_text_field", ownerType="PRODUCT",
         validations=[{"name":"choices","value":json.dumps(MEDIUM_CHOICES)}]),
    dict(name="Line Type", namespace="design", key="line_type", type="single_line_text_field", ownerType="PRODUCT",
         validations=[{"name":"choices","value":json.dumps(LINE_TYPE_CHOICES)}]),
    dict(name="Background Color (Hex)", namespace="design", key="bg_hex", type="color", ownerType="PRODUCT"),
    dict(name="Background Color Name", namespace="design", key="bg_name", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Font Family", namespace="design", key="font_family", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Font Color (Hex)", namespace="design", key="font_color_hex", type="color", ownerType="PRODUCT"),
    dict(name="Font Color Name", namespace="design", key="font_color_name", type="single_line_text_field", ownerType="PRODUCT"),

    # PRODUCT: shapes.*
    dict(name="Shape Archetype", namespace="shapes", key="archetype", type="single_line_text_field", ownerType="PRODUCT",
         validations=[{"name":"choices","value":json.dumps(ARCHETYPE_CHOICES)}]),
    dict(name="Shape Symbols", namespace="shapes", key="symbols", type="single_line_text_field", ownerType="PRODUCT",
         validations=[{"name":"regex","value":"^[↑↓→←↗↘↖↙\s-]+$"}]),

    # PRODUCT: printify.* (optional convenience)
    dict(name="Printify Product ID", namespace="printify", key="product_id", type="single_line_text_field", ownerType="PRODUCT"),

    # VARIANT: printify.*
    dict(name="Printify Blueprint ID", namespace="printify", key="blueprint_id", type="number_integer", ownerType="PRODUCT_VARIANT"),
    dict(name="Printify Provider ID", namespace="printify", key="provider_id", type="number_integer", ownerType="PRODUCT_VARIANT"),
    dict(name="Printify Variant ID", namespace="printify", key="variant_id", type="number_integer", ownerType="PRODUCT_VARIANT"),
    dict(name="Printify SKU", namespace="printify", key="sku", type="single_line_text_field", ownerType="PRODUCT_VARIANT"),
]

DEFINE = """
mutation DefineMetafield($def: MetafieldDefinitionInput!) {
  metafieldDefinitionCreate(definition: $def) {
    createdDefinition {
      id
      name
      namespace
      key
      type { name }   # <-- type is an object now
      ownerType
    }
    userErrors { field message code }
  }
}
"""

PIN = """
mutation PinDef($ownerType: MetafieldOwnerType!, $namespace: String!, $key: String!) {
  metafieldDefinitionPin(ownerType: $ownerType, namespace: $namespace, key: $key) {
    pinnedDefinition { id namespace key ownerType }
    userErrors { field message }
  }
}
"""

def call(query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {"query": query, "variables": variables or {}}
    for attempt in range(3):
        r = requests.post(URL, headers=HDRS, json=payload, timeout=60)
        if r.status_code == 429 and attempt < 2:
            time.sleep(int(r.headers.get("Retry-After","2")))
            continue
        if r.status_code >= 500 and attempt < 2:
            time.sleep(1.5*(attempt+1))
            continue
        data = r.json()
        return data
    return data

def create_all_metafields():
    print(f"Creating {len(DEF_LIST)} definitions on {SHOP} (API {API_VERSION})...")
    for d in DEF_LIST:
        resp = call(DEFINE, {"def": d})
        # Debug: uncomment next line if you need to see raw payloads
        # print(json.dumps(resp, indent=2))

        if "errors" in resp and resp["errors"]:
            print(f" ! GraphQL errors for {d['namespace']}.{d['key']}: {resp['errors']}")
            continue

        node = resp.get("data", {}).get("metafieldDefinitionCreate")
        if not node:
            print(f" ! Unexpected response for {d['namespace']}.{d['key']}: {json.dumps(resp, indent=2)}")
            continue

        uerrs = node.get("userErrors") or []
        created = node.get("createdDefinition")

        if uerrs:
            print(f"- {d['ownerType']}.{d['namespace']}.{d['key']}: {uerrs}")
            continue

        if created:
            tname = created.get("type", {}).get("name")
            print(f"+ Created {created['ownerType']}.{created['namespace']}.{created['key']} (type={tname})")


def pin_some_metafields():
    pins = [
        ("PRODUCT", "story", "slug"),
        ("PRODUCT", "story", "author"),
        ("PRODUCT", "shapes", "archetype"),
        ("PRODUCT", "design", "medium"),
        ("PRODUCT_VARIANT", "printify", "variant_id"),
    ]
    print("Pinning definitions in Admin sidebar...")
    for owner, ns, key in pins:
        resp = call(PIN, {"ownerType": owner, "namespace": ns, "key": key})
        if "errors" in resp and resp["errors"]:
            print(f" ! GraphQL errors while pinning {owner}.{ns}.{key}: {resp['errors']}")
            continue
        node = resp.get("data", {}).get("metafieldDefinitionPin")
        if not node:
            print(f" ! Unexpected response while pinning {owner}.{ns}.{key}: {json.dumps(resp, indent=2)}")
            continue
        uerrs = node.get("userErrors") or []
        if uerrs:
            print(f"- Pin {owner}.{ns}.{key}: {uerrs}")
        else:
            pinned = node.get("pinnedDefinition")
            if pinned:
                print(f"+ Pinned {pinned['ownerType']}.{pinned['namespace']}.{pinned['key']}")




# CREATE METAFIELDS
create_all_metafields()

# PIN METAFIELDS 
# pin_some_metafields()

# ## 
# if __name__ == "__main__":
#     import argparse
#     ap = argparse.ArgumentParser(description="Create Shopify metafield definitions (products & variants).")
#     ap.add_argument("--create", action="store_true", help="Create all definitions")
#     ap.add_argument("--pin", action="store_true", help="Pin common definitions in Admin")
#     args = ap.parse_args()

#     if not (args.create or args.pin):
#         ap.print_help()
#         raise SystemExit(0)

#     if args.create:
#         create_all()
#     if args.pin:
#         pin_some()
