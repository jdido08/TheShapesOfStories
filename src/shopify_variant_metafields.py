import os, requests, json, yaml

def normalize_myshopify_domain(raw: str) -> str:
    s = (raw or "").strip()
    s = s.replace("https://", "").replace("http://", "").split("/")[0]
    if s.endswith(".myshopify.com"):
        s = s[: -len(".myshopify.com")]
    return f"{s}.myshopify.com"

def load_credentials_from_yaml(item):
    with open("/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml", "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config[item]

# -------------------------
# Config
# -------------------------
SHOP_DOMAIN = normalize_myshopify_domain(load_credentials_from_yaml('shopify_url'))
TOKEN = load_credentials_from_yaml('shopify_key')
API_VERSION = "2025-10"
GQL_URL = f"https://{SHOP_DOMAIN}/admin/api/{API_VERSION}/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

def gql(query: str, variables: dict = None):
    r = requests.post(GQL_URL, headers=HEADERS, json={"query": query, "variables": variables or {}})
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], indent=2))
    return data["data"]

# Look up existing definition by namespace/key
QUERY_DEF = """
query GetDef($ownerType: MetafieldOwnerType!, $query: String!) {
  metafieldDefinitions(ownerType: $ownerType, first: 1, query: $query) {
    edges { node { id namespace key type { name } name description ownerType } }
  }
}
"""

# Create / Update mutations
MUT_CREATE = """
mutation CreateDef($definition: MetafieldDefinitionInput!) {
  metafieldDefinitionCreate(definition: $definition) {
    createdDefinition { id namespace key type { name } }
    userErrors { field message code }
  }
}
"""

MUT_UPDATE = """
mutation UpdateDef($definition: MetafieldDefinitionUpdateInput!) {
  metafieldDefinitionUpdate(definition: $definition) {
    updatedDefinition { id namespace key type { name } }
    userErrors { field message code }
  }
}
"""

# --- VARIANT metafield definitions (ownerType = PRODUCTVARIANT) ---
DEFS = [
  # Dimensions & label
  dict(ns="print", key="width_in",       type="number_decimal",          name="Print Width (in)"),
  dict(ns="print", key="height_in",      type="number_decimal",          name="Print Height (in)"),
  dict(ns="print", key="size_label",     type="single_line_text_field",  name="Print Size"),
  dict(ns="print",  key="orientation",    type="single_line_text_field",  name="Orientation", validations=[{"name": "choices", "value": "[\"Portrait\",\"Landscape\",\"Square\",\"Panorama\"]"}]),
  dict(ns="print",  key="dpi",            type="number_integer",          name="DPI"),
  dict(ns="print", key="border_in",     type="number_decimal",          name="Border (in)"),
  dict(ns="print", key="mat_color",     type="color",                   name="Mat Color"),

  # Styles
  dict(ns="print", key="style_label",          type="single_line_text_field",  name="Print Style Label",),
  dict(ns="print", key="line_style",     type="single_line_text_field",  name="Line Style"),

  # Colors & typography
  dict(ns="print", key="background_color",        type="color",                     name="Background Color"),
  dict(ns="print", key="background_color_name",   type="single_line_text_field",    name="Background Color Name"),
  dict(ns="print", key="background_color_family", type="single_line_text_field",    name="Background Color Family"),
  dict(ns="print", key="background_color_shade",  type="single_line_text_field",    name="Background Color Shade"),
  dict(ns="print", key="font_color",              type="color",                     name="Font Color"),
  dict(ns="print", key="font_color_name",         type="single_line_text_field",    name="Font Color Name"),
  dict(ns="print", key="font_color_family",       type="single_line_text_field",    name="Font Color Family"),
  dict(ns="print", key="font_color_shade",        type="single_line_text_field",    name="Font Color Shade"),
  dict(ns="print", key="font_family",             type="single_line_text_field",    name="Font Family"),
  dict(ns="print", key="color_label",             type="single_line_text_field",    name="Print Color Label"),

  # Variant details block
  dict(ns="print", key="details_html",  type="multi_line_text_field",    name="Variant Details (HTML)"),

  # Printify mapping
  dict(ns="printify", key="blueprint_id", type="single_line_text_field", name="Printify Blueprint ID"),
  dict(ns="printify", key="provider_id",  type="single_line_text_field", name="Printify Provider ID"),
  dict(ns="printify", key="variant_id",   type="single_line_text_field", name="Printify Variant ID"),
]

def ensure_definition(owner_type, ns, key, type_name, name, description="", pin=False, validations=None):
    query_str = f"namespace:{ns} key:{key}"
    edges = gql(QUERY_DEF, {"ownerType": owner_type, "query": query_str})["metafieldDefinitions"]["edges"]

    if edges:
        upd_input = {
            "namespace": ns,
            "key": key,
            "ownerType": owner_type,
            "name": name,
            "description": description,
            "pin": pin,
        }
        if validations:
            upd_input["validations"] = validations
        res = gql(MUT_UPDATE, {"definition": upd_input})["metafieldDefinitionUpdate"]
        if res["userErrors"]:
            raise RuntimeError(f"Update error for {ns}.{key}: {res['userErrors']}")
        print(f"✔ Updated {ns}.{key}")
        return res["updatedDefinition"]["id"]

    create_input = {
        "name": name,
        "namespace": ns,
        "key": key,
        "type": type_name,
        "ownerType": owner_type,
        "description": description,
        "pin": pin,
    }
    if validations:
        create_input["validations"] = validations
    res = gql(MUT_CREATE, {"definition": create_input})["metafieldDefinitionCreate"]
    if res["userErrors"]:
        raise RuntimeError(f"Create error for {ns}.{key}: {res['userErrors']}")
    print(f"➕ Created {ns}.{key}")
    return res["createdDefinition"]["id"]

# if __name__ == "__main__":
#     print(f"Seeding VARIANT metafield definitions to {SHOP_DOMAIN} ...")
#     for d in DEFS:
#         ensure_definition(
#             owner_type="PRODUCTVARIANT",
#             ns=d["ns"],
#             key=d["key"],
#             type_name=d["type"],
#             name=d["name"],
#             description=d.get("description",""),
#             pin=False,
#             validations=d.get("validations")
#         )
#     print("Done.")
