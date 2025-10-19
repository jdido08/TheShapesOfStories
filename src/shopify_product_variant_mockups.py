
from typing import Optional, Tuple, Dict, Any, List
import base64
import os
import json
import requests

# Adjust API version to your store's supported stable version as needed.
SHOPIFY_GQL_ENDPOINT_TMPL = "https://{shop_domain}/admin/api/2024-07/graphql.json"


class ShopifyMockups:
    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain
        self.access_token = access_token
        self.endpoint = SHOPIFY_GQL_ENDPOINT_TMPL.format(shop_domain=shop_domain)
        self.session = requests.Session()
        self.session.headers.update({
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })

    def _gql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"query": query, "variables": variables or {}}
        r = self.session.post(self.endpoint, data=json.dumps(payload))
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            raise RuntimeError(f"GraphQL errors: {data['errors']}")
        return data["data"]

    def upload_product_image(self, product_id: str, image_path: str, alt_text: Optional[str] = None) -> Tuple[str, str]:
        """
        Upload a product-level image and return (image_id, image_src).
        product_id: gid://shopify/Product/...
        image_path: local path to a PNG/JPG file
        alt_text: optional alt text for accessibility/SEO
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        with open(image_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode("utf-8")

        mutation = """
        mutation productImageCreate($productId: ID!, $image: ImageInput!) {
          productImageCreate(productId: $productId, image: $image) {
            image {
              id
              url
              altText
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "productId": product_id,
            "image": {
                "originalSource": f"data:image/{self._infer_ext(image_path)};base64,{content_b64}",
                **({"altText": alt_text} if alt_text else {}),
            }
        }
        data = self._gql(mutation, variables)
        res = data["productImageCreate"]
        user_errors = res.get("userErrors") or []
        if user_errors:
            raise RuntimeError(f"productImageCreate errors: {user_errors}")
        img = res["image"]
        return img["id"], img["url"]

    def upload_product_image_from_url(self, product_id: str, image_url: str, alt_text: Optional[str] = None) -> Tuple[str, str]:
        mutation = """
        mutation productImageCreate($productId: ID!, $image: ImageInput!) {
          productImageCreate(productId: $productId, image: $image) {
            image {
              id
              url
              altText
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "productId": product_id,
            "image": {
                "src": image_url,
                **({"altText": alt_text} if alt_text else {}),
            }
        }
        data = self._gql(mutation, variables)
        res = data["productImageCreate"]
        user_errors = res.get("userErrors") or []
        if user_errors:
            raise RuntimeError(f"productImageCreate errors: {user_errors}")
        img = res["image"]
        return img["id"], img["url"]

    def attach_image_to_variant(self, variant_id: str, image_id: str) -> None:
        mutation = """
        mutation productVariantUpdate($input: ProductVariantInput!) {
          productVariantUpdate(input: $input) {
            productVariant {
              id
              image {
                id
                url
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "input": {
                "id": variant_id,
                "imageId": image_id,
            }
        }
        data = self._gql(mutation, variables)
        res = data["productVariantUpdate"]
        user_errors = res.get("userErrors") or []
        if user_errors:
            raise RuntimeError(f"productVariantUpdate errors: {user_errors}")

    def set_variant_mockup_metafield(self, variant_id: str, namespace: str, key: str, value: str, type_: str = "single_line_text_field") -> None:
        mutation = """
        mutation metafieldsSet($metafields: [MetafieldsSetInput!]!) {
          metafieldsSet(metafields: $metafields) {
            metafields {
              id
              namespace
              key
              value
              type
              owner {
                __typename
                ... on ProductVariant { id }
              }
            }
            userErrors {
              field
              message
            }
          }
        }
        """
        variables = {
            "metafields": [{
                "ownerId": variant_id,
                "namespace": namespace,
                "key": key,
                "type": type_,
                "value": value,
            }]
        }
        data = self._gql(mutation, variables)
        res = data["metafieldsSet"]
        user_errors = res.get("userErrors") or []
        if user_errors:
            raise RuntimeError(f"metafieldsSet errors: {user_errors}")

    def bulk_attach_variant_mockups(self, product_id: str, mapping: List[Dict[str, Any]], alt_prefix: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        mapping: list of dicts with keys:
            - variant_id (gid)
            - image_path OR image_url
            - alt (optional)
            - metafield (optional dict): {"namespace": "...", "key": "...", "type": "url" or "single_line_text_field"}
        Returns: list of logs per item.
        """
        logs = []
        for item in mapping:
            v_id = item["variant_id"]
            alt = item.get("alt")
            if (not alt) and alt_prefix:
                alt = f"{alt_prefix} — {v_id.split('/')[-1]}"

            if "image_path" in item:
                img_id, img_src = self.upload_product_image(product_id, item["image_path"], alt_text=alt)
            elif "image_url" in item:
                img_id, img_src = self.upload_product_image_from_url(product_id, item["image_url"], alt_text=alt)
            else:
                raise ValueError("Provide either image_path or image_url for each mapping item.")

            self.attach_image_to_variant(v_id, img_id)

            meta = item.get("metafield")
            if meta:
                mtype = meta.get("type", "url")
                self.set_variant_mockup_metafield(
                    variant_id=v_id,
                    namespace=meta["namespace"],
                    key=meta["key"],
                    value=img_src,
                    type_=mtype,
                )

            logs.append({"variant_id": v_id, "image_id": img_id, "image_src": img_src, "alt": alt})
        return logs

    @staticmethod
    def _infer_ext(path: str) -> str:
        ext = os.path.splitext(path)[1].lower().lstrip(".")
        if ext in {"jpg", "jpeg"}:
            return "jpeg"
        if ext in {"png"}:
            return "png"
        return "png"


def add_shopify_product_variant_mockups(shopify_product_id, shopify_product_variant_id, mockups_paths):
    return 