import requests, time, json
import yaml 

def load_credentials_from_yaml(file_path):
    """Loads API key from a YAML file."""
    with open(file_path, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config["printify_key"]


BASE = "https://api.printify.com/v1"

import re, requests, time

BASE = "https://api.printify.com/v1"

def _req(method, url, headers, **kw):
    for attempt in range(3):
        r = requests.request(method, url, headers=headers, timeout=30, **kw)
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(1.5 * (attempt + 1)); continue
        r.raise_for_status()
        return r
    r.raise_for_status()

def size_to_tuple(any_size_str: str):
    """
    Turn strings like:
      11" x 14", 11″ x 14″, 11 x 14, 11  ×  14,  11-x-14
    into a tuple of ints: (11, 14)
    """
    s = any_size_str.lower()
    # unify separators to 'x'
    s = re.sub(r"[×xX]", "x", s)
    # grab two integer groups around an 'x' with anything between
    m = re.search(r"(\d+)\D*x\D*(\d+)", s)
    if not m:
        raise ValueError(f"Unrecognized size format: {any_size_str!r}")
    return (int(m.group(1)), int(m.group(2)))

def get_variant_by_options(api_token, blueprint_id, provider_id, *, size, paper="Matte"):
    headers = {"Authorization": f"Bearer {api_token}"}
    url = f"{BASE}/catalog/blueprints/{blueprint_id}/print_providers/{provider_id}/variants.json"
    r = _req("GET", url, headers)
    variants = r.json().get("variants", [])

    wanted_wh = size_to_tuple(size)
    wanted_paper = paper.strip().lower()

    # Try exact numeric size + paper match first
    for v in variants:
        opts = v.get("options", {})
        try:
            wh = size_to_tuple(opts.get("size", ""))
        except Exception:
            continue
        if wh == wanted_wh and opts.get("paper", "").strip().lower() == wanted_paper:
            ph = (v.get("placeholders") or [])[0]
            print(f"✅ Variant: id={v['id']} title={v.get('title')} size={opts.get('size')} paper={opts.get('paper')}")
            print(f"   Placeholder: {ph['width']}x{ph['height']} (position {ph['position']})")
            return v["id"], ph, v

    # If not found, show what provider actually offers (normalized)
    available = sorted({(size_to_tuple(v.get("options", {}).get("size","??x??")),
                         v.get("options", {}).get("paper"))
                        for v in variants
                        if "size" in v.get("options", {})})
    raise ValueError(f"No variant for size={wanted_wh}, paper={paper}. "
                     f"Available (WxH, paper): {available}")

def get_blueprint_id_by_title(api_token, blueprint_title):
    """Return blueprint_id for an exact blueprint title."""
    headers = {"Authorization": f"Bearer {api_token}"}
    r = _req("GET", f"{BASE}/catalog/blueprints.json", headers)
    for bp in r.json():
        if bp.get("title") == blueprint_title:
            print(f"✅ Blueprint: {bp['title']} -> {bp['id']}")
            return bp["id"]
    raise ValueError(f"Blueprint not found: {blueprint_title}")

def get_provider_id_by_title(api_token, blueprint_id, provider_title):
    """Return provider_id for an exact provider title under a blueprint."""
    headers = {"Authorization": f"Bearer {api_token}"}
    r = _req("GET", f"{BASE}/catalog/blueprints/{blueprint_id}/print_providers.json", headers)
    providers = r.json()
    for p in providers:
        print(f"- Provider option: {p['title']} (id {p['id']})")
    for p in providers:
        if p.get("title") == provider_title:
            print(f"✅ Provider: {p['title']} -> {p['id']}")
            return p["id"]
    raise ValueError(f"Provider not found for blueprint {blueprint_id}: {provider_title}")

def normalize_size(size_str):
    # "11x14" / "11 x 14" -> '11" x 14"'
    s = size_str.lower().replace('"','').replace(" ", "")
    w, h = s.split('x')
    return f'{int(w)}" x {int(h)}"'




def get_shop_id(api_token, shop_title=None):
    """Return shop_id; if shop_title given, pick by title; else return the first."""
    headers = {"Authorization": f"Bearer {api_token}"}
    r = _req("GET", f"{BASE}/shops.json", headers)
    shops = r.json()
    for s in shops:
        print(f"- Shop: {s['title']} (id {s['id']}) channel={s.get('sales_channel')}")
    if shop_title:
        for s in shops:
            if s.get("title") == shop_title:
                print(f"✅ Using shop: {s['title']} -> {s['id']}")
                return s["id"]
        raise ValueError(f"Shop not found: {shop_title}")
    if not shops:
        raise RuntimeError("No shops returned for this API key")
    print(f"✅ Using first shop -> {shops[0]['id']}")
    return shops[0]["id"]


# API_KEY = load_credentials_from_yaml("/Users/johnmikedidonato/Projects/TheShapesOfStories/config.yaml")
# bp_id = get_blueprint_id_by_title(API_KEY, "Matte Vertical Posters")
# prov_id = get_provider_id_by_title(API_KEY, bp_id, "Printify Choice")
# variant_id, placeholder, _ = get_variant_by_options(API_KEY, bp_id, prov_id, size="11x14", paper="Matte")


#RESPONSE for Matte Vertical Posters, Printify Choice, 11x14, Matte

# ✅ Blueprint: Matte Vertical Posters -> 282
# - Provider option: Printify Choice (id 99)
# - Provider option: Sensaria (id 2)
# ✅ Provider: Printify Choice -> 99
# ✅ Variant: id=43135 title=11″ x 14″ / Matte size=11″ x 14″ paper=Matte
#    Placeholder: 3300x4200 (position front)