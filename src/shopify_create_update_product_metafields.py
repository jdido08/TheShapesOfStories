
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


Practical workflow:
- Add fields? Update DEF_LIST → run create_all_metafields
- Adjust labels/choices? Call metafieldDefinitionUpdate.
- Need a different type/key? New field + migrate.
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
    dict(name="Background Color Family", namespace="design", key="bg_family", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Font Family", namespace="design", key="font_family", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Font Color (Hex)", namespace="design", key="font_color_hex", type="color", ownerType="PRODUCT"),
    dict(name="Font Color Name", namespace="design", key="font_color_name", type="single_line_text_field", ownerType="PRODUCT"),
    dict(name="Font Color Family", namespace="design", key="font_color_family", type="single_line_text_field", ownerType="PRODUCT"),


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

QUERY_DEFS = """
query GetDefs($ownerType: MetafieldOwnerType!, $first: Int!) {
  metafieldDefinitions(ownerType: $ownerType, first: $first) {
    nodes {
      id
      name
      namespace
      key
      ownerType
      type { name }
      description
      validations { name value }
    }
  }
}
"""


UPDATE_DEF = """
mutation UpdateDef($id: ID!, $def: MetafieldDefinitionUpdateInput!) {
  metafieldDefinitionUpdate(id: $id, definition: $def) {
    updatedDefinition {
      id
      name
      description
      type { name }
      validations { name value }
    }
    userErrors { field message code }
  }
}
"""


def get_definition(owner_type: str, namespace: str, key: str) -> Optional[dict]:
    """Return the metafield definition node for (owner_type, namespace, key), or None."""
    resp = call(QUERY_DEFS, {"ownerType": owner_type, "first": 250})
    if "errors" in resp and resp["errors"]:
        print(" ! GraphQL errors in GetDefs:", resp["errors"])
        return None
    nodes = resp.get("data", {}).get("metafieldDefinitions", {}).get("nodes", [])
    for n in nodes:
        if n["namespace"] == namespace and n["key"] == key:
            return n
    return None

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
        ue = resp.get("data",{}).get("metafieldDefinitionPin",{}).get("userErrors") or []
        if ue:
            print(f"- Pin {owner}.{ns}.{key}: {ue}")
        else:
            pinned = resp["data"]["metafieldDefinitionPin"]["pinnedDefinition"]
            print(f"+ Pinned {pinned['ownerType']}.{pinned['namespace']}.{pinned['key']}")

def update_metafield_definition(owner_type: str,
                                namespace: str,
                                key: str,
                                name: Optional[str] = None,
                                description: Optional[str] = None,
                                add_choices: Optional[List[str]] = None,
                                remove_choices: Optional[List[str]] = None,
                                replace_choices: Optional[List[str]] = None,
                                set_regex: Optional[str] = None) -> None:
    """
    - name/description: simple text changes.
    - choices: for single_line_text_field using 'choices' validation.
      Use replace_choices to overwrite, or add/remove to patch.
    - set_regex: replace/define a 'regex' validation value.
    """
    node = get_definition(owner_type, namespace, key)
    if not node:
        print(f" ! Definition not found: {owner_type}.{namespace}.{key}")
        return

    def_input: Dict[str, Any] = {}
    if name is not None:
        def_input["name"] = name
    if description is not None:
        def_input["description"] = description

    # Start from current validations
    curr_validations = node.get("validations", []) or []
    # Build dict -> so we can edit by name
    vmap = {v["name"]: v["value"] for v in curr_validations}

    # Handle choices
    if any([add_choices, remove_choices, replace_choices]):
        # Parse current choices JSON (if present)
        curr_choices = []
        if "choices" in vmap:
            try:
                curr_choices = json.loads(vmap["choices"])
            except Exception:
                curr_choices = []
        if replace_choices is not None:
            new_choices = list(dict.fromkeys(replace_choices))
        else:
            new_choices = list(dict.fromkeys(curr_choices + (add_choices or [])))
            if remove_choices:
                new_choices = [c for c in new_choices if c not in set(remove_choices)]
        vmap["choices"] = _json.dumps(new_choices)

    # Handle regex (completely replace)
    if set_regex is not None:
        vmap["regex"] = set_regex

    # Rebuild validations array from map
    new_validations = [{"name": k, "value": v} for k, v in vmap.items()]
    if new_validations:
        def_input["validations"] = new_validations

    # Call update
    resp = call(UPDATE_DEF, {"id": node["id"], "def": def_input})
    if "errors" in resp and resp["errors"]:
        print(" ! GraphQL errors in UpdateDef:", resp["errors"])
        return
    payload = resp.get("data", {}).get("metafieldDefinitionUpdate")
    if not payload:
        print(" ! Unexpected update response:", json.dumps(resp, indent=2))
        return
    uerrs = payload.get("userErrors") or []
    if uerrs:
        print(" - Update userErrors:", uerrs)
        return
    updated = payload.get("updatedDefinition")
    print(" ✓ Updated:", json.dumps(updated, indent=2))


# CREATE METAFIELDS
#create_all_metafields() ## creates new metafields listed in DEF_LIST

# PIN METAFIELDS 
# pin_some_metafields()

# UPDATE METAFIELDS

## EXAMPLES OF UPDATING METAFIELDS:

# A) Add a new allowed value to design.medium:
# update_metafield_definition(
#     owner_type="PRODUCT",
#     namespace="design",
#     key="medium",
#     add_choices=["poster"]  # appends 'poster' to existing choices
# )

# B) Replace the entire choices list (be careful—tightens validation):
# update_metafield_definition(
#     owner_type="PRODUCT",
#     namespace="design",
#     key="medium",
#     replace_choices=["print","canvas","t-shirt","mug","poster"]
# )


# C) Rename the field as it appears in Admin:
# update_metafield_definition(
#     owner_type="PRODUCT",
#     namespace="story",
#     key="title",
#     name="Story Title (Display)"
# )


# D) Update the regex for shapes.symbols:
# update_metafield_definition(
#     owner_type="PRODUCT",
#     namespace="shapes",
#     key="symbols",
#     set_regex=r"^[↑↓→←↗↘↖↙\s-]+$"  # note: keep the double backslash if this lives inside JSON
# )

#Notes & guardrails
# You cannot change ownerType, namespace, key, or the type of a definition. If those need to change, create a new definition and migrate values.
# Tightening validations (e.g., removing a choice) won’t retroactively delete old values, but future writes with out-of-range values will error. Plan a small data cleanup if needed.
# Your current symbols regex in DEF_LIST should use a double backslash so \s reaches Shopify correctly: