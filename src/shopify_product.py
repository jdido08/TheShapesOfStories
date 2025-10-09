import requests
import json
import base64
import os
import yaml
import requests, json, re

def load_credentials_from_yaml(item, config_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml"):
    with open(config_path, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config[item]

SHOPIFY_URL = "fnjm07-qy.myshopify.com" #maybe put this in YAML?
SHOPIFY_API_TOKEN = load_credentials_from_yaml("shopify_key")

def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", s.lower())
    return re.sub(r"-+", "-", s).strip("-")

def create_shopify_product_with_variants(
    title: str,
    handle: str,
    body_html: str,
    variant_rows: list,
    status: str = "draft"   # "active" when you’re ready
):
    """
    variant_rows: list of dicts like:
      {"colorway":"Purple/Gold","line_type":"StoryBeats","size":"11x14",
       "sku":"<PRINTIFY_SKU>", "price":"24.99"}
    """
    url = f"https://{SHOPIFY_URL}/admin/api/2024-07/products.json"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_API_TOKEN,
        "Content-Type": "application/json"
    }

    payload = {
        "product": {
            "title": title,
            "handle": handle,
            "status": status,
            "body_html": body_html,
            "options": [
                {"name": "Colorway"},
                {"name": "Line type"},
                {"name": "Size"}
            ],
            "variants": [
                {
                    "option1": r["colorway"],
                    "option2": r["line_type"],
                    "option3": r["size"],
                    "sku": r["sku"],                 # <-- MUST equal Printify SKU
                    "price": r["price"],
                    "inventory_policy": "deny",
                    "requires_shipping": True
                } for r in variant_rows
            ]
        }
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
    if resp.status_code not in (200, 201):
        raise RuntimeError(f"Create product failed: {resp.status_code} {resp.text[:400]}")
    product = resp.json()["product"]

    # Build a quick lookup: (colorway,line_type,size) -> variant_id
    vmap = {}
    for v in product["variants"]:
        key = (v.get("option1"), v.get("option2"), v.get("option3"))
        vmap[key] = v["id"]

    return product["id"], product["handle"], vmap

def build_variant_rows_from_printify_mappings(design_mappings, price_by_size):
    """
    design_mappings: list like
      [{
        "colorway":"Purple/Gold",
        "line_type":"StoryBeats",
        "sizes":[
           {"size_label":"11x14","printify_sku":"2932..."},
           {"size_label":"12x18","printify_sku":"4811..."}
        ]
      }, ...]
    price_by_size: dict like {"11x14":"24.99","12x18":"27.99","18x24":"32.99"}
    """
    rows = []
    for d in design_mappings:
        for s in d["sizes"]:
            rows.append({
                "colorway": d["colorway"],
                "line_type": d["line_type"],
                "size": s["size_label"],
                "sku": s["printify_sku"],
                "price": price_by_size[s["size_label"]]
            })
    return rows


###

title = "Romeo and Juliet — Poster"
handle = slugify("Romeo and Juliet — Poster")
body_html = "<p>Your product description HTML here…</p>"

design_mappings = [
  {"colorway":"Purple/Gold","line_type":"StoryBeats","sizes":[
      {"size_label":"11x14","printify_sku":"15345962581165146145"},
  ]}
]
price_by_size = {"11x14":"24.99","12x18":"27.99"}

variant_rows = build_variant_rows_from_printify_mappings(design_mappings, price_by_size)
shopify_product_id, handle, variant_id_map = create_shopify_product_with_variants(
    title, handle, body_html, variant_rows, status="draft"
)
print("Created Shopify product:", shopify_product_id)
print("Variant map:", variant_id_map)  # use these IDs to attach variant-specific images next
