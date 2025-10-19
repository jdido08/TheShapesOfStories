# src/shopify_create_product_variant.py
# Creates Shopify product variants + sets variant metafields
# API: 2025-10

import json
import yaml
import requests
from typing import List, Dict, Any, Optional, Tuple
import time 

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

# ---------- metafield typing (VARIANTS) ----------

VARIANT_TYPE_MAP: Dict[str, str] = {
    # print.*
    "print.width_in":                "number_decimal",
    "print.height_in":               "number_decimal",
    "print.size_label":              "single_line_text_field",
    "print.orientation":             "single_line_text_field",  # Portrait / Landscape
    "print.paper":                   "single_line_text_field",
    "print.frame_included":          "boolean",
    "print.color_label":             "single_line_text_field",
    "print.font_family":             "single_line_text_field",
    "print.style_label":             "single_line_text_field",
    "print.line_style":              "single_line_text_field",
    "print.background_color":        "color",  # hex
    "print.background_color_name":   "single_line_text_field",
    "print.background_color_family": "single_line_text_field",
    "print.background_color_shade":  "single_line_text_field",
    "print.font_color":              "color",  # hex
    "print.font_color_name":         "single_line_text_field",
    "print.font_color_family":       "single_line_text_field",
    "print.font_color_shade":        "single_line_text_field",
    "print.details_html":            "multi_line_text_field",   # large HTML fragment
    # numeric extras you referenced
    "print.dpi":                     "number_integer",
    "print.border_in":               "number_decimal",
    "print.mat_color":               "color",

    # printify.*
    "printify.blueprint_id":         "single_line_text_field",
    "printify.provider_id":          "single_line_text_field",
    "printify.variant_id":           "single_line_text_field",

    # provider SKU (optional)
    "print.provider_variant_id":     "single_line_text_field",
    "print.provider_sku":            "single_line_text_field",
}

def _coerce_value(dotted_key: str, value: Any) -> str:
    mtype = VARIANT_TYPE_MAP[dotted_key]
    if mtype.startswith("list."):
        return json.dumps(value if isinstance(value, list) else [value])
    if mtype == "boolean":
        return "true" if bool(value) else "false"
    return str(value)

# ---------- GraphQL ----------

MUT_PRODUCT_OPTIONS_CREATE = """
mutation($productId: ID!, $options: [OptionCreateInput!]!) {
  productOptionsCreate(productId: $productId, options: $options) {
    product { id options { name position values optionValues { id name hasVariants } } }
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

# ---------- delete variant -----------
# ✅ correct mutation (2025-10)
MUT_PRODUCT_VARIANTS_BULK_DELETE = """
mutation ($productId: ID!, $variantsIds: [ID!]!) {
  productVariantsBulkDelete(productId: $productId, variantsIds: $variantsIds) {
    product { id title }
    userErrors { field message }
  }
}
"""

def delete_variants(product_id: str, variant_ids: list[str]) -> list[str]:
    if not variant_ids:
        return []
    res = gql(MUT_PRODUCT_VARIANTS_BULK_DELETE,
              {"productId": product_id, "variantsIds": variant_ids}
             )["productVariantsBulkDelete"]
    if res["userErrors"]:
        raise RuntimeError(res["userErrors"])
    # API returns the updated product (not the IDs), so just return what we attempted
    return variant_ids


def _key_from_selected_options(selected_options):
    """Return (Size, Color, Style) tuple from a variant's selectedOptions list."""
    by = {o["name"]: o["value"] for o in selected_options}
    return (by.get("Size"), by.get("Color"), by.get("Style"))

def _key_from_bulk_input(variant_input):
    """Return (Size, Color, Style) tuple from your variant bulk input."""
    by = {o["optionName"]: o["name"] for o in variant_input.get("optionValues", [])}
    return (by.get("Size"), by.get("Color"), by.get("Style"))

def build_intended_sets(variants_payload):
    """Return (intended_keys, intended_skus) from your payload."""
    intended_keys = set()
    intended_skus = set()
    for v in variants_payload:
        intended_keys.add(_key_from_bulk_input(v))
        sku = (v.get("inventoryItem") or {}).get("sku")
        if sku:
            intended_skus.add(sku)
    return intended_keys, intended_skus

def find_placeholder_variants(product_id, intended_keys, intended_skus):
    """
    Returns list of variant IDs that look like placeholders:
      - title == 'Default Title'
      - option value '_'
      - missing SKU
      - combo not in intended set
    """
    nodes = list_product_variants(product_id)
    to_delete = []
    for v in nodes:
        title = (v.get("title") or "").strip()
        sku   = (v.get("sku") or "").strip()
        key   = _key_from_selected_options(v.get("selectedOptions") or [])
        so    = v.get("selectedOptions") or []

        # placeholder signals
        if title.lower() == "default title":
            to_delete.append(v["id"])
            continue
        if any(o.get("value") == "_" for o in so):
            to_delete.append(v["id"])
            continue
        if not sku:
            to_delete.append(v["id"])
            continue
        if key not in intended_keys and sku not in intended_skus:
            to_delete.append(v["id"])
    return to_delete



# ---------- helpers ----------

def ensure_product_options(product_id: str, option_names: List[str]) -> None:
    if not option_names:
        return
    current = gql(Q_PRODUCT_OPTIONS, {"id": product_id})["product"]
    existing = current["options"] or []
    if existing:
        return
    opts = []
    for idx, name in enumerate(option_names, start=1):
        opts.append({"name": name, "position": idx, "values": [{"name": "_"}]})
    res = gql(MUT_PRODUCT_OPTIONS_CREATE, {"productId": product_id, "options": opts})["productOptionsCreate"]
    if res["userErrors"]:
        raise RuntimeError(res["userErrors"])

def bulk_create_variants(product_id: str, variants_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    res = gql(MUT_VARIANTS_BULK_CREATE, {"productId": product_id, "variants": variants_data})["productVariantsBulkCreate"]
    if res["userErrors"]:
        raise RuntimeError(res["userErrors"])
    return res["product"]

def list_product_variants(product_id: str) -> List[Dict[str, Any]]:
    edges = gql(Q_PRODUCT_VARIANTS, {"id": product_id})["product"]["variants"]["edges"]
    return [e["node"] for e in edges]

def set_variant_metafields(variant_id: str, values: Dict[str, Any]) -> None:
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
    logs: List[str] = []
    ensure_product_options(product_id, option_names)
    logs.append(f"Ensured product options: {option_names}")

    product_after = bulk_create_variants(product_id, variants)
    logs.append(f"Created variants: total={product_after['totalVariants']}")

    created = list_product_variants(product_id)
    logs.append(f"Fetched {len(created)} variants")

    # Map by SKU primarily; fallback by title
    by_sku = {v.get("sku") or "": v for v in created if v.get("sku")}
    if metafields_for_variant:
        for key, fields in metafields_for_variant.items():
            node = by_sku.get(key) or next((v for v in created if v["title"] == key), None)
            if not node:
                logs.append(f"⚠️ Could not find variant for key '{key}' to set metafields")
                continue
            set_variant_metafields(node["id"], fields)
            logs.append(f"Set {len(fields)} metafields on variant '{key}'")

    return created, logs

# ---------- main entry (your flow) ----------

def create_shopify_product_variant(story_data_path: str, product_type: str, product_slug: str = "ALL", delete_placeholder_variants: bool = True):
    # 1) Load story data
    with open(story_data_path, "r", encoding="utf-8") as f:
        story_data = json.load(f)

    shopify_product_id = story_data.get("shopify_product_id")
    if not shopify_product_id:
        print("❌ ERROR: Missing 'shopify_product_id' in story data.")
        return

    # 2) Get product variants block for this product type
    products_map = story_data.get("products", {})
    product_variants = products_map.get(product_type)
    if product_variants is None:
        print(f"❌ ERROR: No product variants for product type: {product_type}")
        return

    if product_slug != "ALL":
        print("❌ ERROR: SPECIFIC SLUG NOT SUPPORTED AT THIS TIME")
        return

    # 3) Build variants + metafields (ACCUMULATE lists, don’t overwrite)
    option_names = ["Size", "Color", "Style"]
    variants_payload: List[Dict[str, Any]] = []
    metafields_by_sku: Dict[str, Dict[str, Any]] = {}

    for slug, entry in product_variants.items():
        variant_file_path = entry["file_path"]
        variant_sku       = entry["sku"]

        with open(variant_file_path, "r", encoding="utf-8") as f:
            vjson = json.load(f)

        # --- derive print attributes from vjson ---
        size_label = vjson["product_size"]              # e.g., "11x14"
        if size_label == "11x14":
            width_in, height_in, orientation = 11, 14, "Portrait"
        elif size_label == "8x10":
            width_in, height_in, orientation = 8, 10, "Portrait"
        else:
            print(f"❌ ERROR: size '{size_label}' not currently supported")
            return

        dpi = 300
        border_in = (vjson["border_thickness"] / dpi) / 2  # if your JSON is total border, adjust as needed
        mat_color = vjson["border_color_hex"]
        frame_included = False
        paper = "Matte"

        line_style = vjson["line_style"]  # "storybeats" | "classic"
        if line_style == "storybeats":
            style_label = "Storybeats"
        elif line_style == "classic":
            style_label = "Classic"
        else:
            print(f"❌ ERROR: line_style '{line_style}' not currently supported")
            return

        bg_hex   = vjson["background_color_hex"]
        bg_name  = vjson["background_color_name"]
        bg_fam   = vjson["background_color_details"]["family"]
        bg_shade = vjson["background_color_details"]["shade"]

        font_hex   = vjson["font_color_hex"]
        font_name  = vjson["font_color_name"]
        font_fam   = vjson["font_color_details"]["family"]
        font_shade = vjson["font_color_details"]["shade"]

        color_label = f"{bg_name}/{font_name}"
        font_family = vjson["font_style"]
        details_html = vjson["product_description_print_details_html"]

        printify_blueprint_id = vjson.get("printify_blueprint_id")
        printify_provider_id  = vjson.get("printify_provider_id")
        printify_variant_id   = vjson.get("printify_variant_id")

        # --- variant object (for productVariantsBulkCreate) ---
        variants_payload.append({
            "price": 30.00,  # Money can be number or string
            "optionValues": [
                {"optionName": "Size",  "name": size_label},      # e.g., "11x14"
                {"optionName": "Color", "name": color_label},     # e.g., "White/Black"
                {"optionName": "Style", "name": style_label},     # e.g., "Storybeats"
            ],
            "inventoryItem": {
                "sku": variant_sku,        # <-- SKU goes here now
                "tracked": True            # optional, if you track inventory
            }
        })

        # --- per-variant metafields (keyed by SKU) ---
        metafields_by_sku[variant_sku] = {
            "print.width_in": width_in,
            "print.height_in": height_in,
            "print.size_label": size_label,
            "print.orientation": orientation,
            "print.dpi": dpi,
            "print.border_in": border_in,
            "print.mat_color": mat_color,
            "print.frame_included": frame_included,
            "print.paper": paper,
            "print.style_label": style_label,
            "print.line_style": line_style,
            "print.background_color": bg_hex,
            "print.background_color_name": bg_name,
            "print.background_color_family": bg_fam,
            "print.background_color_shade": bg_shade,
            "print.font_color": font_hex,
            "print.font_color_name": font_name,
            "print.font_color_family": font_fam,
            "print.font_color_shade": font_shade,
            "print.font_family": font_family,
            "print.color_label": color_label,
            "print.details_html": details_html,
            "printify.blueprint_id": str(printify_blueprint_id) if printify_blueprint_id is not None else "",
            "printify.provider_id":  str(printify_provider_id)  if printify_provider_id  is not None else "",
            "printify.variant_id":   str(printify_variant_id)   if printify_variant_id   is not None else "",
        }


    # 4) Create variants + set metafields
    created, logs = upsert_variants_with_metafields(
        product_id=shopify_product_id,
        option_names=option_names,
        variants=variants_payload,
        metafields_for_variant=metafields_by_sku,
    )

    print("----- VARIANTS CREATED -----")
    for v in created:
        opts = " / ".join([f"{o['name']}={o['value']}" for o in v["selectedOptions"]])
        print(f"- {v['title']} | SKU={v.get('sku','')} | {opts} | id={v['id']}")

        #save variant id back into both product json and story json  and save 
        #find the right place to add by matching sku
        for slug, entry in product_variants.items(): #product variants part of story data 
            if entry["sku"] == v["sku"]:
                entry["shopify_variant_id"] = v["id"] #add shopify product variant 
                variant_file_path = entry["file_path"]

                with open(variant_file_path, "r", encoding="utf-8") as f:
                    product_variant_data = json.load(f)
                
                product_variant_data['shopify_variant_id'] = v['id']
                product_variant_data['shopify_product_id'] = shopify_product_id


                with open(variant_file_path, "w", encoding="utf-8") as f:     # save it back to the same file
                    json.dump(product_variant_data, f, ensure_ascii=False, indent=2)
                    f.write("\n")  # optional newline at EOF
                time.sleep(1)
                print("✅ Product Variant Data updated w/ Shopify Variant ID and Shopify Product ID")

                story_data['products'][product_type] = product_variants
                with open(story_data_path, "w", encoding="utf-8") as f:     # save it back to the same file
                    json.dump(story_data, f, ensure_ascii=False, indent=2)
                    f.write("\n")  # optional newline at EOF
                time.sleep(1)
                print("✅ Story Data updated w/ Shopify Variant ID")
                

    print("----- LOGS -----")
    for line in logs:
        print(line)

    # Build intended keys/SKUs for later comparison
    intended_keys, intended_skus = build_intended_sets(variants_payload)


    if delete_placeholder_variants:
        placeholder_ids = find_placeholder_variants(shopify_product_id, intended_keys, intended_skus)
        if not placeholder_ids:
            print("🧹 No placeholder or stray variants found.")
        else:
            existing_after = list_product_variants(shopify_product_id)
            if len(existing_after) - len(placeholder_ids) < 1:
                print("⚠️ Refusing to delete: would leave product with zero variants.")
            else:
                deleted = delete_variants(shopify_product_id, placeholder_ids)
                print(f"✅ Deleted placeholder/stray variants: {len(deleted)}")
    



# ---------- testing ----------

if __name__ == "__main__":
    story_data_path = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/story_data/the-stranger-meursault.json"
    create_shopify_product_variant(story_data_path, product_type="print", product_slug="ALL", delete_placeholder_variants=True)
