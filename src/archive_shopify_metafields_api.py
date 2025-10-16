
"""
shopify_metafields_api.py
-------------------------
Create Shopify PRODUCT / VARIANT metafield DEFINITIONS via GraphQL Admin API,
then set values for products and variants (e.g., Printify mapping).

Usage (shell):
  export SHOPIFY_SHOP="your-store.myshopify.com"
  export SHOPIFY_ADMIN_TOKEN="shpat_***"
  export SHOPIFY_API_VERSION="2025-07"   # optional; defaults to 2025-07

  # Dry-run create definitions
  python shopify_metafields_api.py --create-defs

  # Set metafields on a product (by handle) + a variant (by SKU)
  python shopify_metafields_api.py --set-product \
    --handle "the-great-gatsby-jay-gatsby-print" \
    --data-file sample_product_data.json

Notes:
  - GraphQL Admin API endpoint: https://{shop}/admin/api/{version}/graphql.json
  - This script is idempotent-ish: if a definition exists, it logs the error and moves on.
  - metafieldsSet supports up to 25 metafields in a single call (atomic).
"""
import os
import json
import time
from typing import Any, Dict, List, Optional, Tuple
import yaml
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
    print("ERROR: Please set SHOPIFY_SHOP and SHOPIFY_ADMIN_TOKEN environment variables.")
    print("Example: export SHOPIFY_SHOP='your-store.myshopify.com'")
    print("         export SHOPIFY_ADMIN_TOKEN='shpat_***'")
    # don't exit; allow import without env

GRAPHQL_URL = f"https://{SHOP}/admin/api/{API_VERSION}/graphql.json" if SHOP else None
HEADERS = {
    "X-Shopify-Access-Token": TOKEN or "",
    "Content-Type": "application/json"
}

# -------------------------
# GraphQL helpers
# -------------------------
def gql(query: str, variables: Optional[Dict[str, Any]] = None, retries: int = 3) -> Dict[str, Any]:
    if not GRAPHQL_URL:
        raise RuntimeError("GRAPHQL_URL not set; ensure SHOPIFY_SHOP is configured.")
    payload = {"query": query, "variables": variables or {}}
    for attempt in range(retries):
        resp = requests.post(GRAPHQL_URL, headers=HEADERS, json=payload, timeout=60)
        # Handle rate limits (429) gracefully
        if resp.status_code == 429 and attempt < retries - 1:
            retry_after = int(resp.headers.get("Retry-After", "2"))
            time.sleep(retry_after)
            continue
        if resp.status_code >= 500 and attempt < retries - 1:
            time.sleep(1.5 * (attempt + 1))
            continue
        try:
            data = resp.json()
        except Exception:
            resp.raise_for_status()
            raise
        if "errors" in data and attempt < retries - 1:
            # Retry transient errors
            time.sleep(1.0 * (attempt + 1))
            continue
        return data
    return data  # last response

# -------------------------
# Definitions to create
# -------------------------

# You can edit choices below to match your catalog.
MEDIUM_CHOICES = ["print", "canvas", "t-shirt", "mug"]
LINE_TYPE_CHOICES = ["line", "text"]
ARCHETYPE_CHOICES = ["Icarus", "Man in Hole", "Cinderella", "Boy Meets Girl", "Oedipus", "Rags to Riches", "From Bad to Worse"]

DEF_LIST: List[dict] = [
    # -------- PRODUCT: story.* --------
    dict(name="Story Slug", namespace="story", key="slug", type="single_line_text_field", ownerType="PRODUCT",
         validations=[{"name": "regex", "value": "^[a-z0-9-]+$"}]),
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

    # -------- PRODUCT: design.* --------
    dict(name="Medium", namespace="design", key="medium", type="single_line_text_field", ownerType="PRODUCT",
         validations=[{"name": "choices", "value": json.dumps(MEDIUM_CHOICES)}]),
    dict(name="Line Type", namespace="design", key="line_type", type="single_line_text_field", ownerType="PRODUCT",
         validations=[{"name": "choices", "value": json.dumps(LINE_TYPE_CHOICES)}]),
    dict(name="Background Color (Hex)", namespace="design", key="bg_hex", type="color", ownerType="PRODUCT"),
    dict(name="Background Color Name", namespace="design", key="bg_name", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Font Family", namespace="design", key="font_family", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Font Color (Hex)", namespace="design", key="font_color_hex", type="color", ownerType="PRODUCT"),
    dict(name="Font Color Name", namespace="design", key="font_color_name", type="single_line_text_field", ownerType="PRODUCT"),

    # -------- PRODUCT: shapes.* --------
    dict(name="Shape Archetype", namespace="shapes", key="archetype", type="single_line_text_field", ownerType="PRODUCT",
         validations=[{"name": "choices", "value": json.dumps(ARCHETYPE_CHOICES)}]),
    dict(name="Shape Symbols", namespace="shapes", key="symbols", type="single_line_text_field", ownerType="PRODUCT",
         validations=[{"name": "regex", "value": "^[↑↓→←↗↘↖↙\s-]+$"}]),

    # -------- PRODUCT: printify.* (optional convenience) --------
    dict(name="Printify Product ID", namespace="printify", key="product_id", type="single_line_text_field", ownerType="PRODUCT"),

    # -------- VARIANT: printify.* --------
    dict(name="Printify Blueprint ID", namespace="printify", key="blueprint_id", type="number_integer", ownerType="PRODUCT_VARIANT"),
    dict(name="Printify Provider ID", namespace="printify", key="provider_id", type="number_integer", ownerType="PRODUCT_VARIANT"),
    dict(name="Printify Variant ID", namespace="printify", key="variant_id", type="number_integer", ownerType="PRODUCT_VARIANT"),
    dict(name="Printify SKU", namespace="printify", key="sku", type="single_line_text_field", ownerType="PRODUCT_VARIANT"),
]

# A mapping of (namespace, key) -> type so we don't repeat types when setting values
FIELD_TYPES: Dict[Tuple[str, str], str] = {(d["namespace"], d["key"]): d["type"] for d in DEF_LIST}

# -------------------------
# GraphQL documents
# -------------------------
DEFINE_MUTATION = """
mutation DefineMetafield($def: MetafieldDefinitionInput!) {
  metafieldDefinitionCreate(definition: $def) {
    createdDefinition { id name namespace key type ownerType }
    userErrors { field message }
  }
}
"""

PIN_MUTATION = """
mutation PinDef($ownerType: MetafieldOwnerType!, $namespace: String!, $key: String!) {
  metafieldDefinitionPin(ownerType: $ownerType, namespace: $namespace, key: $key) {
    pinnedDefinition { id namespace key ownerType }
    userErrors { field message }
  }
}
"""

METAFIELDS_SET = """
mutation SetMetafields($metafields: [MetafieldsSetInput!]!) {
  metafieldsSet(metafields: $metafields) {
    metafields { id namespace key type value owner { __typename ... on Product { id } ... on ProductVariant { id } } }
    userErrors { field message }
  }
}
"""

PRODUCT_BY_HANDLE = """
query ($handle: String!) {
  productByHandle(handle: $handle) {
    id
    title
    handle
    variants(first: 250) {
      nodes {
        id
        sku
        title
        selectedOptions { name value }
      }
    }
  }
}
"""

# -------------------------
# Definition creation / pinning
# -------------------------
def create_definitions(defs: List[dict]) -> None:
    print(f"Creating {len(defs)} metafield definitions...")
    for d in defs:
        data = gql(DEFINE_MUTATION, {"def": d})
        errs = data.get("data", {}).get("metafieldDefinitionCreate", {}).get("userErrors") or []
        if errs:
            # Common: "Key has already been taken"
            print(f" - {d['ownerType']}.{d['namespace']}.{d['key']}: userErrors -> {errs}")
        else:
            created = data.get("data", {}).get("metafieldDefinitionCreate", {}).get("createdDefinition")
            print(f" + Created {created['ownerType']}.{created['namespace']}.{created['key']} ({created['type']})")

def pin_core_defs(defs: List[dict]) -> None:
    # Pin handy fields so they appear in the admin sidebar
    print("Pinning common definitions...")
    core = [
        ("PRODUCT", "story", "slug"),
        ("PRODUCT", "story", "author"),
        ("PRODUCT", "shapes", "archetype"),
        ("PRODUCT", "design", "medium"),
        ("PRODUCT_VARIANT", "printify", "variant_id"),
    ]
    for owner, ns, key in core:
        data = gql(PIN_MUTATION, {"ownerType": owner, "namespace": ns, "key": key})
        errs = data.get("data", {}).get("metafieldDefinitionPin", {}).get("userErrors") or []
        if errs:
            print(f" - Pin {owner}.{ns}.{key}: userErrors -> {errs}")
        else:
            pinned = data["data"]["metafieldDefinitionPin"]["pinnedDefinition"]
            print(f" + Pinned {pinned['ownerType']}.{pinned['namespace']}.{pinned['key']}")

# -------------------------
# Setters
# -------------------------
def _as_value(ns: str, key: str, value: Any) -> Tuple[str, str]:
    """
    Return (type, serialized_value) for a metafield based on the definition type.
    For list.* types, the value must be JSON-encoded string.
    """
    mtype = FIELD_TYPES[(ns, key)]
    if mtype.startswith("list."):
        if not isinstance(value, (list, tuple)):
            raise ValueError(f"Value for {ns}.{key} must be a list for type {mtype}")
        return mtype, json.dumps(list(value), ensure_ascii=False)
    elif mtype == "color":
        # Shopify expects a hex color like "#RRGGBB"
        if not isinstance(value, str) or not value.startswith("#") or len(value) not in (4, 7):
            raise ValueError(f"Color for {ns}.{key} must be a hex string like #0A1F3B")
        return mtype, value
    elif mtype in ("number_integer", "number_decimal"):
        return mtype, str(value)
    else:
        # text-like types (single_line_text_field, multiline_text_field, etc.)
        return mtype, str(value)

def set_product_metafields_by_handle(handle: str, values: Dict[Tuple[str, str], Any]) -> None:
    """values is a dict of (namespace, key) -> python value"""
    prod = gql(PRODUCT_BY_HANDLE, {"handle": handle}).get("data", {}).get("productByHandle")
    if not prod:
        raise RuntimeError(f"Product not found for handle: {handle}")
    owner_id = prod["id"]
    entries = []
    for (ns, key), pyval in values.items():
        if (ns, key) not in FIELD_TYPES:
            raise KeyError(f"Definition not known for {ns}.{key}. Add it to DEF_LIST first.")
        mtype, sval = _as_value(ns, key, pyval)
        entries.append({
            "ownerId": owner_id,
            "namespace": ns,
            "key": key,
            "type": mtype,
            "value": sval
        })
    # Batch in chunks of 25
    for i in range(0, len(entries), 25):
        batch = entries[i:i+25]
        data = gql(METAFIELDS_SET, {"metafields": batch})
        errs = data.get("data", {}).get("metafieldsSet", {}).get("userErrors") or []
        if errs:
            raise RuntimeError(f"metafieldsSet userErrors: {errs}")
    print(f"Set {len(entries)} metafields on product {handle}")

def set_variant_metafields_by_sku(handle: str, sku_to_values: Dict[str, Dict[Tuple[str, str], Any]]) -> None:
    """Find variants on a product (by handle), then set metafields by matching SKU"""
    prod = gql(PRODUCT_BY_HANDLE, {"handle": handle}).get("data", {}).get("productByHandle")
    if not prod:
        raise RuntimeError(f"Product not found for handle: {handle}")
    variants = {v["sku"]: v["id"] for v in prod["variants"]["nodes"] if v.get("sku")}
    missing = [sku for sku in sku_to_values.keys() if sku not in variants]
    if missing:
        raise RuntimeError(f"Variant SKU(s) not found on product: {missing}")
    entries = []
    for sku, kv in sku_to_values.items():
        owner_id = variants[sku]
        for (ns, key), pyval in kv.items():
            if (ns, key) not in FIELD_TYPES:
                raise KeyError(f"Definition not known for {ns}.{key}. Add it to DEF_LIST first.")
            mtype, sval = _as_value(ns, key, pyval)
            entries.append({
                "ownerId": owner_id,
                "namespace": ns,
                "key": key,
                "type": mtype,
                "value": sval
            })
    # Batch in chunks of 25
    for i in range(0, len(entries), 25):
        batch = entries[i:i+25]
        data = gql(METAFIELDS_SET, {"metafields": batch})
        errs = data.get("data", {}).get("metafieldsSet", {}).get("userErrors") or []
        if errs:
            raise RuntimeError(f"metafieldsSet userErrors: {errs}")
    print(f"Set {len(entries)} metafields across {len(sku_to_values)} variant(s) on product {handle}")

# -------------------------
# CLI
# -------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Create Shopify metafield definitions and set values.")
    parser.add_argument("--create-defs", action="store_true", help="Create metafield definitions.")
    parser.add_argument("--pin-defs", action="store_true", help="Pin select definitions in admin.")
    parser.add_argument("--set-product", action="store_true", help="Set product metafields by handle.")
    parser.add_argument("--set-variants", action="store_true", help="Set variant metafields by SKU on a product.")
    parser.add_argument("--handle", help="Product handle (for set-product / set-variants).")
    parser.add_argument("--data-file", help="JSON file with values mapping.")
    args = parser.parse_args()

    # Safety checks
    if not SHOP or not TOKEN:
        raise SystemExit("Set SHOPIFY_SHOP and SHOPIFY_ADMIN_TOKEN env vars before running.")

    if args.create_defs:
        create_definitions(DEF_LIST)

    if args.pin_defs:
        pin_core_defs(DEF_LIST)

    # Data-file format examples:
    # For --set-product: {
    #   ["story","slug"]: "the-great-gatsby",
    #   ["story","title"]: "The Great Gatsby",
    #   ["story","author"]: "F. Scott Fitzgerald",
    #   ["story","genre"]: ["Classics","Novel"],
    #   ["design","medium"]: "print",
    #   ["shapes","archetype"]: "Icarus",
    #   ["shapes","symbols"]: "↑↓"
    # }
    #
    # For --set-variants: {
    #   "SKU-123": {
    #     ["printify","blueprint_id"]: 12345,
    #     ["printify","provider_id"]: 67890,
    #     ["printify","variant_id"]: 111213,
    #     ["printify","sku"]: "PRINTIFY-SKU-123"
    #   }
    # }
    def _load_kv_map(path: str) -> Dict:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        # Convert stringified "['ns','key']" into tuple keys when present
        norm = {}
        for k, v in raw.items():
            if isinstance(k, list) and len(k) == 2:
                norm[tuple(k)] = v
            elif isinstance(k, str) and k.startswith("[") and k.endswith("]"):
                try:
                    arr = json.loads(k)
                    if isinstance(arr, list) and len(arr) == 2:
                        norm[tuple(arr)] = v
                    else:
                        norm[k] = v
                except Exception:
                    norm[k] = v
            else:
                norm[k] = v
        return norm

    if args.set_product:
        if not args.handle or not args.data_file:
            raise SystemExit("--set-product requires --handle and --data-file")
        kv = _load_kv_map(args.data_file)
        # Filter only tuple keys (ns,key)
        values = {k: v for k, v in kv.items() if isinstance(k, tuple) and len(k) == 2}
        set_product_metafields_by_handle(args.handle, values)

    if args.set_variants:
        if not args.handle or not args.data_file:
            raise SystemExit("--set-variants requires --handle and --data-file")
        raw = _load_kv_map(args.data_file)  # expects { sku: { (ns,key): value, ... }, ... }
        # Normalize nested keys
        sku_map = {}
        for sku, inner in raw.items():
            if not isinstance(inner, dict):
                raise SystemExit("Data file for --set-variants must map SKU -> { [ns,key]: value, ... }")
            norm_inner = {}
            for k, v in inner.items():
                if isinstance(k, tuple):
                    norm_inner[k] = v
                elif isinstance(k, list) and len(k) == 2:
                    norm_inner[tuple(k)] = v
                elif isinstance(k, str) and k.startswith("["):
                    try:
                        arr = json.loads(k)
                        if isinstance(arr, list) and len(arr) == 2:
                            norm_inner[tuple(arr)] = v
                    except Exception:
                        pass
            sku_map[sku] = norm_inner
        set_variant_metafields_by_sku(args.handle, sku_map)
