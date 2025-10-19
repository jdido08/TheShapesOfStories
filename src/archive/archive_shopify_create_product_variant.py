# src/shopify_create_product_variant.py
# Creates Shopify product variants + sets variant metafields
# API: 2025-10

import os
import json
import yaml
import requests
from typing import List, Dict, Any, Optional, Tuple

# ---------- credentials / HTTP ----------

def normalize_myshopify_domain(raw: str) -> str:
    s = (raw or "").strip()
    s = s.replace("https://", "").replace("http://", "").split("/")[0]
    if s.endswith(".myshopify.com"):
        s = s[: -len(".myshopify.com")]
    return f"{s}.myshopify.com"

def load_credentials_from_yaml(item: str):
    with open("/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml", "r") as f:
        config = yaml.safe_load(f)
    return config[item]

SHOP_DOMAIN = normalize_myshopify_domain(load_credentials_from_yaml("shopify_url"))
TOKEN       = load_credentials_from_yaml("shopify_key")
API_VERSION = "2025-10"

GQL_URL = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

def gql(query: str, variables: Dict[str, Any] = None) -> Dict[str, Any]:
    r = requests.post(GQL_URL, headers=HEADERS, json={"query": query, "variables": variables or {}})
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], indent=2))
    return data["data"]

# ---------- metafield typing ----------

# Define the metafield types for VARIANTS (not products)
VARIANT_TYPE_MAP: Dict[str, str] = {
    # print.*
    "print.width_in":              "number_decimal",
    "print.height_in":             "number_decimal",
    "print.size_label":            "single_line_text_field",
    "print.orientation":           "single_line_text_field",  # "Vertical" / "Horizontal"
    "print.paper":                 "single_line_text_field",  # "Matte" / "Glossy" / provider value
    "print.frame_included":        "boolean",
    "print.provider_variant_id":   "single_line_text_field",  # e.g., Printify variant id
    "print.provider_sku":          "single_line_text_field",
    # add more as needed...
}

def _coerce_value(dotted_key: str, value: Any) -> str:
    """Return the correct string payload for metafieldsSet.value based on type."""
    mtype = VARIANT_TYPE_MAP[dotted_key]
    if mtype.startswith("list."):
        return json.dumps(value if isinstance(value, list) else [value])
    if mtype == "boolean":
        return "true" if bool(value) else "false"
    return str(value)

# ---------- GraphQL: mutations & queries ----------

MUT_PRODUCT_OPTIONS_CREATE = """
mutation($productId: ID!, $options: [OptionCreateInput!]!) {
  productOptionsCreate(productId: $productId, options: $options) {
    product {
      id
      options { name position values optionValues { id name hasVariants } }
    }
    userErrors { field message code }
  }
}
"""

MUT_VARIANTS_BULK_CREATE = """
mutation($productId: ID!, $variants: [ProductVariantsBulkInput!]!) {
  productVariantsBulkCreate(productId: $productId, variants: $variants) {
    product {
      id
      title
      totalVariants
      variants(first: 250) {
        edges {
          node {
            id
            title
            price
            sku
            selectedOptions { name value }
          }
        }
      }
    }
    userErrors { field message code }
  }
}
"""

MUT_METAFIELDS_SET = """
mutation($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { id namespace key type value }
    userErrors { field message }
  }
}
"""

Q_PRODUCT_OPTIONS = """
query($id: ID!) {
  product(id: $id) {
    id
    options { name position values }
  }
}
"""

Q_PRODUCT_VARIANTS = """
query($id: ID!) {
  product(id: $id) {
    id
    title
    variants(first: 250) {
      edges {
        node {
          id
          title
          sku
          selectedOptions { name value }
        }
      }
    }
  }
}
"""

# ---------- helpers ----------

def ensure_product_options(product_id: str, option_names: List[str]) -> None:
    """
    Ensure the product has the expected option names in order.
    If product has no options, create them; if it already has options, no-op.
    """
    if not option_names:
        return
    current = gql(Q_PRODUCT_OPTIONS, {"id": product_id})["product"]
    existing = current["options"] or []
    if existing:
        # Already present; you can add validation here if you need exact name/order.
        return

    opts = []
    for idx, name in enumerate(option_names, start=1):
        # Shopify requires at least one value to create an option. Seed a throwaway value.
        opts.append({"name": name, "position": idx, "values": [{"name": "_"}]})
    res = gql(MUT_PRODUCT_OPTIONS_CREATE, {"productId": product_id, "options": opts})["productOptionsCreate"]
    if res["userErrors"]:
        raise RuntimeError(res["userErrors"])

def bulk_create_variants(product_id: str, variants_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create variants in bulk. `variants_data` is a list of ProductVariantsBulkInput.
    Returns the product block from the mutation response.
    """
    payload = {"productId": product_id, "variants": variants_data}
    res = gql(MUT_VARIANTS_BULK_CREATE, payload)["productVariantsBulkCreate"]
    if res["userErrors"]:
        raise RuntimeError(res["userErrors"])
    return res["product"]

def list_product_variants(product_id: str) -> List[Dict[str, Any]]:
    """Return a flat list of variant nodes with id/title/sku/selectedOptions."""
    edges = gql(Q_PRODUCT_VARIANTS, {"id": product_id})["product"]["variants"]["edges"]
    return [e["node"] for e in edges]

def set_variant_metafields(variant_id: str, values: Dict[str, Any]) -> None:
    """Set metafields for a single variant using VARIANT_TYPE_MAP typing."""
    if not values:
        return
    mf_inputs = []
    for dotted_key, val in values.items():
        if dotted_key not in VARIANT_TYPE_MAP:
            raise ValueError(f"Unknown variant metafield key: {dotted_key}")
        ns, key = dotted_key.split(".", 1)
        mf_inputs.append({
            "ownerId": variant_id,
            "namespace": ns,
            "key": key,
            "type": VARIANT_TYPE_MAP[dotted_key],
            "value": _coerce_value(dotted_key, val),
        })
    res = gql(MUT_METAFIELDS_SET, {"metafields": mf_inputs})["metafieldsSet"]
    if res["userErrors"]:
        raise RuntimeError(res["userErrors"])

# ---------- orchestration ----------

def upsert_variants_with_metafields(
    product_id: str,
    option_names: List[str],
    variants: List[Dict[str, Any]],
    metafields_for_variant: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Ensure options exist, create variants, then set metafields per variant.
    - option_names: e.g., ["Color", "Style", "Size"]
    - variants: list of dicts each like:
        {
          "title": "11x14 / Storybeats / Charcoal Beige",
          "price": "30.00",
          "sku": "PRINT-11x14-STORYBEATS-CHARCOAL-BEIGE",
          "options": [
             {"name": "Size", "value": "11x14"},
             {"name": "Style", "value": "Storybeats"},
             {"name": "Color", "value": "Charcoal Beige"}
          ]
        }
    - metafields_for_variant: optional mapping keyed by a stable key (e.g., SKU or tuple of option values)
        {
          "PRINT-11x14-STORYBEATS-CHARCOAL-BEIGE": {
             "print.width_in": 11,
             "print.height_in": 14,
             "print.size_label": "11x14",
             "print.paper": "Matte",
             "print.orientation": "Vertical"
          },
          ...
        }

    Returns: (variant_nodes, logs)
    """
    logs: List[str] = []
    ensure_product_options(product_id, option_names)
    logs.append(f"Ensured product options: {option_names}")

    product_after = bulk_create_variants(product_id, variants)
    logs.append(f"Created variants: total={product_after['totalVariants']}")

    created = list_product_variants(product_id)  # get IDs + selectedOptions + SKU
    logs.append(f"Fetched {len(created)} variants")

    # Map by SKU (primary) or by option triple if no SKU
    by_sku: Dict[str, Dict[str, Any]] = {v.get("sku") or "": v for v in created if v.get("sku")}
    if metafields_for_variant:
        for k, fields in metafields_for_variant.items():
            # prefer SKU match, else try to match by title
            node = by_sku.get(k)
            if not node:
                # fallback: match by title if provided as key
                node = next((v for v in created if v["title"] == k), None)
            if not node:
                logs.append(f"⚠️ Could not find variant for key '{k}' to set metafields")
                continue
            set_variant_metafields(node["id"], fields)
            logs.append(f"Set {len(fields)} metafields on variant '{k}'")

    return created, logs

# ---------- example usage ----------

#product_slug specifies whether to create one or all product variants for a certain product type
def create_shopify_product_varaint(story_data_path, product_type, product_slug="ALL"):
    
    #open story data with product path 
    with open(story_data_path, 'r') as f:
        story_data = json.load(f)
    shopify_product_id = story_data['shopify_product_id']
    
    #get product variants 
    product_variants = story_data['products'].get(product_type, None)
    if product_variants == None:
        print("❌ ERROR: No product variants for product type: ", product_type, " found")
        return 
    
    if product_slug != "ALL":
        print("❌ ERROR: SPECIFIC SLUG NOT SUPPORTED AT THIS TIME")
        return 

    if product_type == "print":
        for key, value in product_variants.items():
            product_variant_slug = key
            product_variant_file_path = value['file_path']
            product_varaint_sku = value['sku']
            product_options = ["Size", "Color", "Style"]

            with open(product_variant_file_path, 'r') as f:
                product_variant_data = json.load(f)

            #print details
            if product_variant_data['product_size'] == "11x14":
                product_variant_width_in = 11
                product_variant_height_in = 14
                product_variant_orientation = "Portrait"
            else:
                print("❌ ERROR: ", product_variant_data['product_size'], " not currently supported")
                return 
        
            product_variant_size_label = product_variant_data['product_size']
            product_variant_dpi = 300
            product_variant_border_in = ((product_variant_data['border_thickness']/product_variant_dpi)/2)
            product_variant_mat_color = product_variant_data['border_color_name']
            product_variant_frame_included = False
            product_variant_paper = "Matte"

            if product_variant_data['line_style'] == "storybeats":
                product_variant_style_label = "Storybeats"
            elif product_variant_data['line_style'] == "classic":
                product_variant_style_label = "Classic"
            else:
                print("❌ ERROR: ", product_variant_data['line_style'], " not currently supported")
                return 
            
            product_variant_line_style = product_variant_data['line_style']


            #color details 
            product_variant_background_color = product_variant_data['background_color_hex']
            product_variant_background_color_name = product_variant_data['background_color_name']
            product_variant_background_color_family = product_variant_data['background_color_details']['family']
            product_variant_background_color_shade = product_variant_data['background_color_details']['shade']
            product_variant_font_color = product_variant_data['font_color_hex']
            product_variant_font_color_name = product_variant_data['font_color_name']
            product_variant_font_color_family = product_variant_data['font_color_details']['family']
            product_variant_font_color_shade = product_variant_data['font_color_details']['shade']
            product_variant_color_label = product_variant_background_color_name + "/" + product_variant_font_color_name
            
            product_variant_font_family = product_variant_data['font_style']

            product_variant_print_details_html = product_variant_data['story_print_details_product_description_html']

            product_variant_printify_blueprint_id = product_variant_data['printify_blueprint_id']
            product_variant_printify_provider_id = product_variant_data['printify_provider_id']
            product_variant_printify_variant_id = product_variant_data['printify_variant_id']


            product_variant_data = {
                "title": f"{product_variant_size_label} / {product_variant_color_label} / {product_variant_style_label}",
                "price": "30.00",
                "sku": product_varaint_sku,
                "options": [
                    {"name": "Size",  "value": product_variant_size_label},
                    {"name": "Color", "value": product_variant_color_label},
                    {"name": "Style", "value": product_variant_style_label},
                ]
            }

            product_variant_metafields = {
                "print.width_in": product_variant_width_in,
                "print.height_in": product_variant_height_in,
                "print.size_label": product_variant_size_label,
                "print.orientation": product_variant_orientation,
                "print.dpi": product_variant_dpi,
                "print.border_in": product_variant_border_in,
                "print.mat_color": product_variant_mat_color,
                "print.frame_included": product_variant_frame_included,
                "print.paper": product_variant_paper,
                "print.style_label": product_variant_style_label,
                "print.line_style": product_variant_line_style,
                "print.background_color": product_variant_background_color,
                "print.background_color_name": product_variant_background_color_name,
                "print.background_color_family": product_variant_background_color_family,
                "print.background_color_shade": product_variant_background_color_shade,
                "print.font_color": product_variant_font_color,
                "print.font_color_name": product_variant_font_color_name,
                "print.font_color_family": product_variant_font_color_family,
                "print.font_color_shade": product_variant_font_color_shade,
                "print.font_family": product_variant_font_family,
                "print.color_label": product_variant_color_label,
                "print.details_html": product_variant_print_details_html,
                "printify.blueprint_id": product_variant_printify_blueprint_id,
                "printify.provider_id": product_variant_printify_provider_id,
                "printify.variant_id": product_variant_printify_variant_id
            }
    else:
        print("❌ ERROR: ", product_type, " not currently supported")
        return 
    

    created, logs = upsert_variants_with_metafields(
        product_id=shopify_product_id,
        option_names=product_options,
        variants=product_variant_data,
        metafields_for_variant=product_variant_metafields,
    )

    print("----- VARIANTS CREATED -----")
    for v in created:
        opts = " / ".join([f"{o['name']}={o['value']}" for o in v["selectedOptions"]])
        print(f"- {v['title']} | SKU={v.get('sku','')} | {opts} | id={v['id']}")

    print("----- LOGS -----")
    for line in logs:
        print(line)

    return

    

#TESTING 
story_data_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/story_data/the-stranger-meursault.json"
product_type = "print"
product_slug = "ALL"
create_shopify_product_varaint(story_data_path, product_type, product_slug)


