import os, requests, json, yaml

### THIS IS FOR CREATING AND/OR UPDATING SHOPIFY PRODUCT METAFIELDS ###

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

# Look up an existing definition by namespace/key
QUERY_DEF = """
query GetDef($ownerType: MetafieldOwnerType!, $query: String!) {
  metafieldDefinitions(ownerType: $ownerType, first: 1, query: $query) {
    edges { node { id namespace key type { name } name description ownerType } }
  }
}
"""

# Create / Update
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


# Your schema (PRODUCT ownerType)
# --- DEFS (comment out story.ref for now) ---
DEFS = [
  dict(ns="story", key="title",                type="single_line_text_field",      name="Story Title"),
  dict(ns="story", key="protagonist",          type="single_line_text_field",      name="Story Protagonist"),
  dict(ns="story", key="slug",                 type="single_line_text_field",      name="Story Slug"),
  dict(ns="story", key="year",                 type="number_integer",              name="Story Year"),
  dict(ns="story", key="type",                 type="single_line_text_field",      name="Story Type"),
  dict(ns="story", key="manual_collections",   type="list.single_line_text_field",   name="Manual Collections"),
  dict(ns="shape", key="symbolic_representation", type="single_line_text_field",   name="Shape: Symbolic Representation"),
  dict(ns="shape", key="archetype",               type="single_line_text_field",   name="Shape: Archetype"),
  dict(ns="literature", key="author",             type="single_line_text_field",   name="Author"),
  dict(ns="literature", key="genres",             type="list.single_line_text_field", name="Genres"),
  dict(ns="literature", key="themes",             type="list.single_line_text_field", name="Themes"),
  dict(ns="literature", key="settings",           type="list.single_line_text_field", name="Settings"),
  dict(ns="literature", key="countries",          type="list.single_line_text_field", name="Countries"),
  dict(ns="literature", key="series_or_universe", type="list.single_line_text_field", name="Series or Universe"),
  dict(ns="literature", key="awards",             type="list.single_line_text_field", name="Awards"),
  dict(ns="literature", key="primary_isbns",      type="list.single_line_text_field", name="Primary ISBNs"),
]




def ensure_definition(owner_type, ns, key, type_name, name, description="", pin=False, validations=None):
    query_str = f"namespace:{ns} key:{key}"
    edges = gql(QUERY_DEF, {"ownerType": owner_type, "query": query_str})["metafieldDefinitions"]["edges"]

    if edges:
        # Build the update input with the REQUIRED identifiers:
        upd_input = {
            "namespace": ns,
            "key": key,
            "ownerType": owner_type,
            # Updatable fields:
            "name": name,
            "description": description,
            "pin": pin,
            # Optionally: "validations": [...]
        }
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


# --- main loop (no extra kwargs) ---
# if __name__ == "__main__":

#     print(f"Seeding product metafield definitions to {SHOP_DOMAIN} ...")
#     for d in DEFS:
#         ensure_definition(
#             owner_type="PRODUCT",
#             ns=d["ns"],
#             key=d["key"],
#             type_name=d["type"],
#             name=d["name"],
#             description=d.get("description",""),
#             pin=False,                      # set True if you want them pinned in Admin
#             validations=d.get("validations")
#         )
#     print("Done.")
