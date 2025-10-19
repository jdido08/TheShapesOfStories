import os, requests, json, time
from typing import Optional, List, Dict
import yaml

def load_credentials_from_yaml(item, config_path="/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml"):
    with open(config_path, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config[item]

# SHOP = load_credentials_from_yaml('shopify_url')
SHOP = "fnjm07-qy"
TOKEN = load_credentials_from_yaml('shopify_key')
API_VERSION = "2025-10"  # ok to bump later
GQL_URL = f"https://{SHOP}.myshopify.com/admin/api/{API_VERSION}/graphql.json"
HEADERS = {"X-Shopify-Access-Token": TOKEN, "Content-Type": "application/json"}

def gql(query: str, variables: dict | None = None):
    r = requests.post(GQL_URL, headers=HEADERS, json={"query": query, "variables": variables or {}})
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(json.dumps(data["errors"], indent=2))
    return data["data"]

# ---- 1) LIST & DELETE DEFINITIONS ----
QUERY_DEFINITIONS = """
query MetafieldDefinitions($ownerType: MetafieldOwnerType!, $cursor: String) {
  metafieldDefinitions(ownerType: $ownerType, first: 100, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        name
        namespace
        key
        type { name }
        ownerType
      }
    }
  }
}
"""

MUT_DEFINITION_DELETE = """
mutation MetafieldDefinitionDelete($id: ID!, $deleteAllAssociatedMetafields: Boolean!) {
  metafieldDefinitionDelete(id: $id, deleteAllAssociatedMetafields: $deleteAllAssociatedMetafields) {
    deletedDefinitionId
    userErrors { field message code }
  }
}
"""


def list_all_definitions(owner_type: str) -> List[Dict]:
    """owner_type: 'PRODUCT' or 'PRODUCTVARIANT'"""
    out = []
    cursor = None
    while True:
        data = gql(QUERY_DEFINITIONS, {"ownerType": owner_type, "cursor": cursor})["metafieldDefinitions"]
        out.extend([e["node"] for e in data["edges"]])
        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]
    return out

def delete_definitions(owner_type: str, dry_run: bool, sleep_sec: float = 0.15) -> int:
    defs = list_all_definitions(owner_type)
    print(f"{owner_type}: found {len(defs)} metafield definitions")
    deleted = 0
    for d in defs:
        info = f"{d['id']}  {d['namespace']}.{d['key']}  ({d['type']['name']})"
        if dry_run:
            print(f"[DRY-RUN] Would delete definition: {info}")
            continue
        res = gql(MUT_DEFINITION_DELETE, {"id": d["id"], "deleteAllAssociatedMetafields": True})["metafieldDefinitionDelete"]
        if res["userErrors"]:
            print(f"⚠️  Could not delete definition {info} -> {res['userErrors']}")
        else:
            deleted += 1
        time.sleep(sleep_sec)
    if not dry_run:
        print(f"✅ {owner_type}: deleted {deleted} definitions (requested {len(defs)})")
    return deleted

# ---- 2) CLEAN UP ANY UNMANAGED METAFIELD VALUES ----
QUERY_PRODUCTS = """
query ProductsWithMetafields($cursor: String) {
  products(first: 50, after: $cursor) {
    pageInfo { hasNextPage endCursor }
    edges {
      node {
        id
        handle
        metafields(first: 250) { edges { node { namespace key } } }
        variants(first: 100) {
          edges {
            node {
              id
              sku
              metafields(first: 250) { edges { node { namespace key } } }
            }
          }
        }
      }
    }
  }
}
"""

MUT_METAFIELDS_DELETE = """
mutation MetafieldsDelete($metafields: [MetafieldIdentifierInput!]!) {
  metafieldsDelete(metafields: $metafields) {
    deletedMetafields { ownerId namespace key }
    userErrors { field message }
  }
}
"""

def delete_all_unmanaged_values(dry_run: bool, batch_size: int = 50, sleep_sec: float = 0.25):
    total_to_delete = 0
    actually_deleted = 0
    cursor = None
    while True:
        data = gql(QUERY_PRODUCTS, {"cursor": cursor})["products"]
        for edge in data["edges"]:
            p = edge["node"]
            ids = []

            # product-level
            for me in p["metafields"]["edges"]:
                node = me["node"]
                ids.append({"ownerId": p["id"], "namespace": node["namespace"], "key": node["key"]})

            # variant-level
            for ve in p["variants"]["edges"]:
                v = ve["node"]
                for me in v["metafields"]["edges"]:
                    node = me["node"]
                    ids.append({"ownerId": v["id"], "namespace": node["namespace"], "key": node["key"]})

            if not ids:
                continue

            total_to_delete += len(ids)
            if dry_run:
                print(f"[DRY-RUN] Would delete {len(ids)} metafields for product {p['handle']} ({p['id']})")
                continue

            # delete in chunks
            for i in range(0, len(ids), batch_size):
                chunk = ids[i:i+batch_size]
                res = gql(MUT_METAFIELDS_DELETE, {"metafields": chunk})["metafieldsDelete"]
                if res["userErrors"]:
                    print(f"⚠️ userErrors on metafieldsDelete: {res['userErrors']}")
                actually_deleted += len(res["deletedMetafields"])
                time.sleep(sleep_sec)

        if not data["pageInfo"]["hasNextPage"]:
            break
        cursor = data["pageInfo"]["endCursor"]

    if dry_run:
        print(f"[DRY-RUN] Unmanaged metafields that would be deleted: {total_to_delete}")
    else:
        print(f"✅ Deleted unmanaged metafields: {actually_deleted} (requested {total_to_delete})")

# ---- 3) DRIVER ----
if __name__ == "__main__":
    # Flip to False to actually delete.
    DRY_RUN = False

    print("== Metafield Definition Deletion ==")
    delete_definitions("PRODUCT", dry_run=DRY_RUN)
    delete_definitions("PRODUCTVARIANT", dry_run=DRY_RUN)

    print("\n== Unmanaged Metafield Value Cleanup ==")
    delete_all_unmanaged_values(dry_run=DRY_RUN)

    if DRY_RUN:
        print("\n[DRY-RUN] Review counts above. If everything looks good, set DRY_RUN=False and run again.")
