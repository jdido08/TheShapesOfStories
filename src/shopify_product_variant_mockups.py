
from typing import Optional, Tuple, Dict, Any, List
import base64
import os
import json
import requests, yaml, time


from PIL import Image, ImageOps
import os
MAX_PIXELS = 20_000_000  # Shopify hard limit
def downscale_to_20mp_inplace(path: str, max_pixels: int = MAX_PIXELS) -> None:
    """
    If `path` points to an image >20MP, resizes it in-place (same filename)
    keeping aspect ratio. Uses high-quality resampling. Preserves format.
    """
    with Image.open(path) as im:
        # Honor EXIF orientation for JPEGs
        im = ImageOps.exif_transpose(im)
        w, h = im.size
        pixels = w * h
        if pixels <= max_pixels:
            return  # already fine

        scale = (max_pixels / pixels) ** 0.5
        new_w = max(1, int(w * scale))
        new_h = max(1, int(h * scale))
        im = im.resize((new_w, new_h), Image.LANCZOS)

        fmt = (im.format or os.path.splitext(path)[1].lstrip(".")).upper()
        save_kwargs = {}
        if fmt in ("JPG", "JPEG"):
            # Sensible defaults for JPEG
            save_kwargs.update(dict(quality=92, optimize=True, progressive=True))
            fmt = "JPEG"
        elif fmt == "PNG":
            # Keep transparency; try to optimize
            save_kwargs.update(dict(optimize=True))
        # Overwrite same file
        im.save(path, format=fmt, **save_kwargs)
        print(f"ℹ️ Downscaled in-place {os.path.basename(path)}: {w}x{h} → {new_w}x{new_h}")


from PIL import Image, ImageCms

import os, io, tempfile
from PIL import Image, ImageCms

import os, io, tempfile
from PIL import Image, ImageCms

def normalize_for_shopify(src_path: str, max_edge: int = 5000, flatten_bg=None) -> str:
    """
    Normalizes an image IN-PLACE at src_path for Shopify:
      - 8-bit sRGB
      - RGB (or RGBA if keeping alpha); optional alpha flatten to a bg color
      - Long edge <= max_edge (default 5000px) using LANCZOS
      - Saves as PNG (optimized, non-interlaced) OVERWRITING src_path atomically
    Returns src_path.
    """
    im = Image.open(src_path)

    # Ensure 8-bit channel & compatible mode
    if im.mode not in ("RGB", "RGBA"):
        im = im.convert("RGBA")

    # Convert to sRGB if an ICC profile exists
    try:
        icc = im.info.get("icc_profile")
        if icc:
            src_prof = ImageCms.ImageCmsProfile(io.BytesIO(icc))
            dst_prof = ImageCms.createProfile("sRGB")
            im = ImageCms.profileToProfile(im, src_prof, dst_prof, outputMode=im.mode)
    except Exception:
        # If profile conversion fails, continue with current image
        pass

    # Optionally flatten alpha onto a background
    if im.mode == "RGBA" and flatten_bg is not None:
        bg = Image.new("RGB", im.size, flatten_bg)
        bg.paste(im, mask=im.split()[-1])
        im = bg  # now RGB (no alpha)

    # Clamp dimensions if needed
    w, h = im.size
    long_edge = max(w, h)
    if long_edge > max_edge:
        scale = max_edge / float(long_edge)
        im = im.resize((int(round(w*scale)), int(round(h*scale))), Image.LANCZOS)

    # Atomic overwrite to avoid partial writes
    dir_, base = os.path.split(src_path)
    with tempfile.NamedTemporaryFile(delete=False, dir=dir_, suffix=".png") as tmp:
        tmp_path = tmp.name
    try:
        im.save(tmp_path, format="PNG", optimize=True)
        os.replace(tmp_path, src_path)  # atomic on POSIX
    finally:
        if os.path.exists(tmp_path):
            try: os.remove(tmp_path)
            except OSError: pass

    return src_path



def clip_alt(text: str, max_len: int = 512) -> str:
    return (text[: max_len - 1] + "…") if len(text) > max_len else text


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


class ShopifyMockups:
    def __init__(self, shop_domain: str, access_token: str):
        self.shop_domain = shop_domain
        self.access_token = access_token
        # Use the live domain you calculated above; ignore format() on GQL_URL
        self.endpoint = f"https://{self.shop_domain}/admin/api/{API_VERSION}/graphql.json"
        self.session = requests.Session()
        self.session.headers.update({
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
    
    def wait_until_media_ready(self, media_id: str, timeout_sec: float = 20.0, poll_every: float = 0.5) -> None:
        """
        Polls product media by ID until status == READY or times out (best-effort).
        """
        import time
        start = time.time()
        while time.time() - start < timeout_sec:
            st = self.get_media_status(media_id)  # implement via product { media(id: ...) { status } }
            if st == "READY":
                return
            time.sleep(poll_every)
        # Non-fatal timeout; proceed anyway


    def get_variant_media_ids(self, variant_id: str) -> List[str]:
        q = """
        query ($id: ID!) {
        productVariant(id: $id) {
            id
            media(first: 100) {
            nodes { id }
            }
        }
        }
        """
        data = self._gql(q, {"id": variant_id})
        nodes = (((data or {}).get("productVariant") or {}).get("media") or {}).get("nodes") or []
        return [n["id"] for n in nodes if n and n.get("id")]
    
    def ensure_media_on_variant(self, product_id: str, variant_id: str, media_ids: list[str]) -> list[str]:
        """
        Append media to variant, skipping ones already attached.
        Returns the list of media IDs that were actually appended.
        """
        if not media_ids:
            return []

        existing = set(self.get_variant_media_ids(variant_id))
        to_add = [m for m in media_ids if m not in existing]
        if not to_add:
            return []

        mutation = """
        mutation ($productId: ID!, $variantMedia: [ProductVariantAppendMediaInput!]!) {
        productVariantAppendMedia(productId: $productId, variantMedia: $variantMedia) {
            userErrors { field message code }
        }
        }
        """
        variables = {
            "productId": product_id,
            # IMPORTANT: one entry per media to append
            "variantMedia": [{"variantId": variant_id, "mediaIds": [m]} for m in to_add],
        }
        data = self._gql(mutation, variables)
        errs = (data["productVariantAppendMedia"] or {}).get("userErrors") or []
        if errs:
            # If Shopify says "already has media", re-check and treat as success if attached.
            only_already = all(e.get("code") == "PRODUCT_VARIANT_ALREADY_HAS_MEDIA" for e in errs)
            if only_already:
                now = set(self.get_variant_media_ids(variant_id))
                if set(to_add).issubset(now):
                    return to_add
            raise RuntimeError(f"productVariantAppendMedia errors: {errs}")

        return to_add


    def reorder_variant_media(self, product_id: str, variant_id: str, ordered_media_ids: List[str]) -> None:
        """
        Puts the given media IDs at the front of the variant's media in the specified order.
        Leaves other media (if any) after them, preserving their relative order.
        """
        # Current order
        current = self.get_variant_media_ids(variant_id)
        if not current or not ordered_media_ids:
            return

        # Build desired final order
        #  - take our desired ids in order (if present in current)
        #  - then append remaining current ids that aren't in our desired list
        want = [m for m in ordered_media_ids if m in current]
        tail = [m for m in current if m not in set(want)]
        final = want + tail
        if final == current:
            return  # already in desired order

        # Build "moves" for productVariantReorderMedia
        # We'll put the first wanted media FIRST, then each next AFTER the previous
        moves = []
        if want:
            prev = None
            for idx, m in enumerate(want):
                if idx == 0:
                    moves.append({"id": m, "newPosition": "FIRST"})
                else:
                    moves.append({"id": m, "newPosition": f"AFTER:{prev}"})
                prev = m

        mutation = """
        mutation ($productId: ID!, $variantId: ID!, $moves: [MoveInput!]!) {
        productVariantReorderMedia(productId: $productId, variantId: $variantId, moves: $moves) {
            userErrors { field message code }
        }
        }
        """
        variables = {"productId": product_id, "variantId": variant_id, "moves": moves}
        data = self._gql(mutation, variables)
        errs = (data["productVariantReorderMedia"] or {}).get("userErrors") or []
        if errs:
            raise RuntimeError(f"productVariantReorderMedia errors: {errs}")



    def _gql(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        payload = {"query": query, "variables": variables or {}}
        r = self.session.post(self.endpoint, data=json.dumps(payload))
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            raise RuntimeError(f"GraphQL errors: {data['errors']}")
        return data["data"]
    
    import time

    def _find_recent_media_by_alt(self, product_id: str, alt_text: str) -> Optional[str]:
        """
        Look for a recent IMAGE media on the product that matches alt_text.
        Returns the MediaImage node ID if found, else None.
        """
        q = """
        query($id: ID!) {
        product(id: $id) {
            media(first: 50) {
            nodes {
                __typename
                ... on MediaImage {
                id
                alt
                mediaContentType
                status
                preview { image { id url } }
                }
            }
            }
        }
        }
        """
        data = self._gql(q, {"id": product_id})
        nodes = (data.get("product") or {}).get("media", {}).get("nodes", []) or []
        # Prefer exact alt match; fall back to first IMAGE with PROCESSING/READY
        for n in nodes:
            if n.get("__typename") == "MediaImage" and (n.get("alt") or "") == alt_text:
                return n.get("id")
        for n in nodes[::-1]:  # scan newest-ish first
            if n.get("__typename") == "MediaImage" and n.get("mediaContentType") == "IMAGE":
                return n.get("id")
        return None


    def _wait_for_media_preview(self, media_id: str, *, timeout_s: int = 30, poll_interval_s: float = 1.0) -> Tuple[str, str]:
        """
        Polls the media node until preview.image is available or timeout.
        Returns (product_image_id, image_url).
        Raises RuntimeError on timeout or failed status.
        """
        q = """
        query ($ids: [ID!]!) {
        nodes(ids: $ids) {
            ... on MediaImage {
            id
            status        # EXPECTED: PROCESSING | READY | FAILED
            preview {
                image { id url altText }
            }
            }
        }
        }
        """
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            data = self._gql(q, {"ids": [media_id]})
            node = (data.get("nodes") or [None])[0]
            if not node:
                time.sleep(poll_interval_s)
                continue

            status = node.get("status")
            preview = (node.get("preview") or {}).get("image")

            if status == "FAILED":
                raise RuntimeError("Media processing failed for image.")
            if preview and preview.get("id") and preview.get("url"):
                return preview["id"], preview["url"]

            # still processing
            time.sleep(poll_interval_s)

        raise RuntimeError("Timed out waiting for media preview.image to be generated.")

    def upload_product_image(self, product_id: str, image_path: str, alt_text: Optional[str] = None) -> Tuple[str, str]:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        filename  = os.path.basename(image_path)
        mime      = "image/png" if image_path.lower().endswith(".png") else "image/jpeg"
        file_size = str(os.path.getsize(image_path))  # UnsignedInt64 must be STRING

        # 1) staged upload
        staged_mutation = """
        mutation stagedUploadsCreate($input: [StagedUploadInput!]!) {
        stagedUploadsCreate(input: $input) {
            stagedTargets { url resourceUrl parameters { name value } }
            userErrors { field message }
        }
        }
        """
        staged_vars = {
            "input": [{
                "resource": "IMAGE",
                "filename": filename,
                "mimeType": mime,
                "httpMethod": "POST",
                "fileSize": file_size,
            }]
        }
        staged_data = self._gql(staged_mutation, staged_vars)
        su = staged_data["stagedUploadsCreate"]
        if su.get("userErrors"):
            raise RuntimeError(f"stagedUploadsCreate errors: {su['userErrors']}")

        target       = su["stagedTargets"][0]
        post_url     = target["url"]
        resource_url = target["resourceUrl"]
        fields       = {p["name"]: p["value"] for p in target["parameters"]}

        # 2) POST file to S3
        with open(image_path, "rb") as f:
            files = {"file": (filename, f, mime)}
            resp = requests.post(post_url, data=fields, files=files)
        if not (200 <= resp.status_code < 400):
            raise RuntimeError(f"S3 upload failed: {resp.status_code} {resp.text[:300]}")

        # 3) Create media on product (IMAGE) — mediaContentType inside the media item
        media_mutation = """
        mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
        productCreateMedia(productId: $productId, media: $media) {
            media {
            id
            mediaContentType
            preview { image { id url altText } }
            }
            mediaUserErrors { field message }
        }
        }
        """
        media_vars = {
            "productId": product_id,
            "media": [{
                "originalSource": resource_url,
                "mediaContentType": "IMAGE",
                **({"alt": alt_text} if alt_text else {}),
            }]
        }
        media_data = self._gql(media_mutation, media_vars)
        pcm = media_data["productCreateMedia"]
        if pcm.get("mediaUserErrors"):
            raise RuntimeError(f"productCreateMedia errors: {pcm['mediaUserErrors']}")

        # Sometimes Shopify returns [None] while processing starts — filter those out
        media_items = [m for m in (pcm.get("media") or []) if m]
        if not media_items:
            if alt_text:
                media_id = self._find_recent_media_by_alt(product_id, alt_text)
                if not media_id:
                    raise RuntimeError("No media nodes returned and could not locate media by alt on product.")
                return self._wait_for_media_preview(media_id, timeout_s=90, poll_interval_s=1.0)
            else:
                raise RuntimeError("No media nodes returned from productCreateMedia and no alt provided to locate it.")

        media_node = media_items[0]  # <- use the filtered list

        media_id = media_node["id"]  # <-- MediaImage GID


        preview_img = (media_node.get("preview") or {}).get("image") or {}
        if preview_img.get("id") and preview_img.get("url"):
            return preview_img["id"], preview_img["url"], media_id

        img_id, img_url = self._wait_for_media_preview(media_id, timeout_s=90, poll_interval_s=1.0)
        return img_id, img_url, media_id

    def upload_product_image_from_url(self, product_id: str, image_url: str, alt_text: Optional[str] = None) -> Tuple[str, str, str]:
        media_mutation = """
        mutation productCreateMedia($productId: ID!, $media: [CreateMediaInput!]!) {
        productCreateMedia(productId: $productId, media: $media) {
            media {
            id
            mediaContentType
            preview { image { id url altText } }
            }
            mediaUserErrors { field message }
        }
        }
        """
        media_vars = {
            "productId": product_id,
            "media": [{
                "originalSource": image_url,
                "mediaContentType": "IMAGE",
                **({"alt": alt_text} if alt_text else {}),
            }]
        }
        media_data = self._gql(media_mutation, media_vars)
        pcm = media_data["productCreateMedia"]
        if pcm.get("mediaUserErrors"):
            raise RuntimeError(f"productCreateMedia errors: {pcm['mediaUserErrors']}")

        media_items = [m for m in (pcm.get("media") or []) if m]
        if not media_items:
            # try to find it by alt, then poll
            if alt_text:
                media_id = self._find_recent_media_by_alt(product_id, alt_text)
                if not media_id:
                    raise RuntimeError("No media nodes returned and could not locate media by alt on product.")
                img_id, img_url = self._wait_for_media_preview(media_id, timeout_s=90, poll_interval_s=1.0)
                return img_id, img_url, media_id
            raise RuntimeError("No media nodes returned from productCreateMedia and no alt provided to locate it.")

        media_node = media_items[0]
        media_id = media_node["id"]
        preview_img = (media_node.get("preview") or {}).get("image") or {}
        if preview_img.get("id") and preview_img.get("url"):
            return preview_img["id"], preview_img["url"], media_id

        img_id, img_url = self._wait_for_media_preview(media_id, timeout_s=90, poll_interval_s=1.0)
        return img_id, img_url, media_id


    def attach_media_to_variant(self, product_id: str, variant_id: str, media_id: str) -> None:
        mutation = """
        mutation ($productId: ID!, $variantMedia: [ProductVariantAppendMediaInput!]!) {
        productVariantAppendMedia(productId: $productId, variantMedia: $variantMedia) {
            userErrors { field message code }
        }
        }
        """
        variables = {
            "productId": product_id,
            "variantMedia": [{"variantId": variant_id, "mediaIds": [media_id]}],  # <-- array
        }
        data = self._gql(mutation, variables)
        errs = (data["productVariantAppendMedia"] or {}).get("userErrors") or []
        if errs:
            raise RuntimeError(f"productVariantAppendMedia errors: {errs}")

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
                img_id, img_src, media_id = self.upload_product_image(product_id, item["image_path"], alt_text=alt)
            elif "image_url" in item:
                img_id, img_src, media_id = self.upload_product_image_from_url(product_id, item["image_url"], alt_text=alt)
            else:
                raise ValueError("Provide either image_path or image_url for each mapping item.")

            self.attach_media_to_variant(product_id, v_id, media_id)

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


def fetch_product_and_one_variant_metafields(sdk, product_gid: str, variant_gid: str):
    q = """
    query GetProductAndVariantMeta($productId: ID!, $variantId: ID!) {
      product(id: $productId) {
        id
        title
        handle
        metafields(first: 250) {
          nodes { namespace key type value }
        }
      }
      productVariant(id: $variantId) {
        id
        title
        sku
        selectedOptions { name value }
        metafields(first: 250) {
          nodes { namespace key type value }
        }
      }
    }
    """
    data = sdk._gql(q, {"productId": product_gid, "variantId": variant_gid})
    return {
        "product": {
            "id": data["product"]["id"],
            "title": data["product"]["title"],
            "handle": data["product"]["handle"],
            "metafields": data["product"]["metafields"]["nodes"],
        },
        "variant": {
            "id": data["productVariant"]["id"],
            "title": data["productVariant"]["title"],
            "sku": data["productVariant"]["sku"],
            "selectedOptions": data["productVariant"]["selectedOptions"],
            "metafields": data["productVariant"]["metafields"]["nodes"],
        },
    }


import json

def get_meta(meta_list, namespace, key, default=None, parse=True):
    for m in meta_list:
        if m.get("namespace") == namespace and m.get("key") == key:
            val = m.get("value")
            if not parse:
                return val

            t = m.get("type", "")
            # Parse list.* values which are stored as JSON strings
            if t.startswith("list.") and isinstance(val, str):
                try:
                    return json.loads(val)
                except Exception:
                    return default if default is not None else val
            # Convert numbers
            if t == "number_integer":
                try: return int(val)
                except: return default if default is not None else val
            if t == "number_decimal":
                try: return float(val)
                except: return default if default is not None else val

            return val
    return default



def add_shopify_product_variant_mockups(product_data_path: str) -> Dict[str, Any]:
    """
    Upload all mockups at the PRODUCT level.
    Attach ONLY the first successfully uploaded image as the VARIANT's native primary.
    Write:
      - variant metafield mockup.primary (url)
      - variant metafield mockup.gallery (list.url)  # JSON array string
    Return a small summary dict.
    """
    # --- load product data
    with open(product_data_path, "r") as f:
        product_data = json.load(f)

    mockups_paths      = product_data.get("mockup_paths") or []
    product_sku        = product_data.get("sku")
    shopify_product_id = product_data.get("shopify_product_id")
    shopify_variant_id = product_data.get("shopify_variant_id")

    if not shopify_product_id or not shopify_variant_id:
        raise ValueError("Missing shopify_product_id or shopify_variant_id in product_data JSON.")
    if not mockups_paths:
        raise ValueError("mockups_paths is empty; nothing to upload.")

    # --- SDK
    sdk = ShopifyMockups(shop_domain=SHOP_DOMAIN, access_token=TOKEN)

    # --- fetch metafields (for alt-text)
    all_meta_fields   = fetch_product_and_one_variant_metafields(sdk, shopify_product_id, shopify_variant_id)
    product_metafields = all_meta_fields["product"]["metafields"] or []
    variant_metafields = all_meta_fields["variant"]["metafields"] or []

    def nz(v, default=""):
        return v if (v is not None and v != "null") else default

    story_title       = nz(get_meta(product_metafields, "story", "title"))
    story_protagonist = nz(get_meta(product_metafields, "story", "protagonist"))
    story_author      = nz(get_meta(product_metafields, "literature", "author"))
    story_shape       = nz(get_meta(product_metafields, "shape", "symbolic_representation"))
    story_archetype   = nz(get_meta(product_metafields, "shape", "archetype"))

    product_size  = nz(get_meta(variant_metafields, "print", "size_label"))
    product_style = nz(get_meta(variant_metafields, "print", "style_label"))
    product_color = nz(get_meta(variant_metafields, "print", "color_label"))

    left  = " — ".join([p for p in [story_title, story_protagonist, story_author] if p])
    mid   = " — ".join([p for p in [story_shape, story_archetype] if p])
    right = " — ".join([p for p in [product_size, product_style, product_color] if p])
    base_alt = " | ".join([s for s in [left, mid, right] if s])

    uploaded_urls: List[str] = []
    uploaded_media_ids: List[str] = []

    for path in mockups_paths:
        if not os.path.exists(path):
            print(f"⚠️  Skipping missing mockup file: {path}")
            continue

        # infer a view label by filename suffix
        view = ""
        if path.endswith("-poster.png"):
            view = "Poster"
        elif path.endswith("-table.png"):
            view = "Table — Frame"
        elif path.endswith("-wall.png"):
            view = "Wall — Frame"
        elif path.endswith("-3x_wall.png"):
            view = "Gallery Wall — Frame"

        pieces = [base_alt]
        if view:
            pieces.append(view)
        if product_sku:
            pieces.append(f"SKU: {product_sku}")
        alt_text = " | ".join([p for p in pieces if p])
        alt_text = clip_alt(alt_text)  # ensure this helper exists; trims ~512 chars

        #downscale_to_20mp_inplace(path)
        normalize_for_shopify(path)                   # keeps alpha


        # Upload to PRODUCT
        img_id, img_url, media_id = sdk.upload_product_image(shopify_product_id, path, alt_text=alt_text)

        # Optional but stabilizing: wait until media is READY (no-op if you haven't implemented)
        try:
            sdk.wait_until_media_ready(media_id, timeout_sec=20, poll_every=0.5)
        except AttributeError:
            pass  # if helper isn't implemented, just proceed

        uploaded_urls.append(img_url)
        uploaded_media_ids.append(media_id)

    if not uploaded_urls:
        raise FileNotFoundError("None of the mockup files could be uploaded (all missing or invalid).")

    # Choose primary from the FIRST SUCCESSFUL upload (not necessarily index 0 of input list)
    primary_media_id = uploaded_media_ids[0]
    primary_url      = uploaded_urls[0]

    # HYBRID: attach ONLY the primary to the VARIANT, then reorder so it's first (idempotent)
    sdk.ensure_media_on_variant(shopify_product_id, shopify_variant_id, [primary_media_id])
    sdk.reorder_variant_media(shopify_product_id, shopify_variant_id, [primary_media_id])

    # Write metafields
    sdk.set_variant_mockup_metafield(shopify_variant_id, "mockup", "primary", primary_url, type_="url")
    sdk.set_variant_mockup_metafield(
        shopify_variant_id, "mockup", "gallery", json.dumps(uploaded_urls), type_="list.url"
    )

    result = {
        "variant_id": shopify_variant_id,
        "primary_media_id": primary_media_id,
        "primary_url": primary_url,
        "gallery_urls": uploaded_urls,
        "count_uploaded": len(uploaded_urls),
    }
    print(f"✅ Uploaded {len(uploaded_urls)} mockups; attached 1 primary to variant; metafields written.")
    return result


add_shopify_product_variant_mockups("/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/product_data/the-stranger-meursault-print-11x14-helvetica-neue-white-gray.json")