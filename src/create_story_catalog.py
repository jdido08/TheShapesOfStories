#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Build a story catalog from JSON files and write it to a Google Sheet (by Spreadsheet ID).

Auth:
- Loads Google service-account creds from YAML at PATHS['config'] (expects a top-level
  key "google_sheets" containing the service account JSON fields).
- Scopes include Sheets + Drive.

VS Code use:
- Edit CONFIG below and press Run.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

# ----------------------- CONFIG (edit these) -----------------------
ROOT_DIR = "/Users/johnmikedidonato/Library/CloudStorage/GoogleDrive-johnmike@theshapesofstories.com/My Drive/story_data"      # e.g. "/Users/you/.../story_data"
SPREADSHEET_ID = "16tmqmaXRN_a_TV4iWdkHkJb4XPgc7dKKZZzd7dVtQs4"       # the long key in the sheet URL
WORKSHEET_NAME = "Catalog"
CSV_OUT = None                                    # e.g. "/tmp/story_catalog.csv" or None
GLOB_PATTERN = "*.json"
# -------------------------------------------------------------------

# Optional: import PATHS from your repo (needed for YAML creds path)
PATHS = None
try:
    from paths import PATHS as _PATHS
    PATHS = _PATHS
except Exception:
    PATHS = None

# Google Sheets / Auth
import gspread
import yaml
from google.oauth2.service_account import Credentials

# Columns (no color fields)
COLUMNS = [
    "story_type",
    "story title",
    "story_author",
    "story_protagonist",
    "story_year",
    "shape_symbolic_representation",
    "shape_archetype",
    "shopify_product_id",
    "story data file path",
    "count of print products",
    "print product slugs",
    "print product sku's",
    "print product filepaths",
    "print product shopify_variant_id",
]

# -------------------- Data extraction --------------------

def _extract_row(path: Path) -> Dict[str, Any]:
    data = json.loads(path.read_text())

    prints = (data.get("products", {}) or {}).get("print", {}) or {}
    slugs = list(prints.keys())
    skus  = [prints[s].get("sku") for s in slugs]
    fps   = [prints[s].get("file_path") for s in slugs]
    vids  = [prints[s].get("shopify_variant_id") for s in slugs]

    nl = "\n"  # newline-delimit lists for readability in Sheets

    return {
        "story_type": data.get("story_type"),
        "story title": data.get("title"),
        "story_author": data.get("author"),
        "story_protagonist": data.get("protagonist"),
        "story_year": data.get("year"),
        "shape_symbolic_representation": data.get("shape_symbolic_representation"),
        "shape_archetype": data.get("shape_archetype"),
        "shopify_product_id": data.get("shopify_product_id"),
        "story data file path": str(path),
        "count of print products": len(prints),
        "print product slugs": nl.join(slugs),
        "print product sku's": nl.join([s for s in skus if s]),
        "print product filepaths": nl.join([f for f in fps if f]),
        "print product shopify_variant_id": nl.join([v for v in vids if v]),
    }

def build_rows(root: str | Path, pattern: str = "*.json") -> List[Dict[str, Any]]:
    root = Path(root).expanduser()
    if not root.exists():
        raise FileNotFoundError(f"Root folder not found: {root}")
    files = sorted(root.rglob(pattern))
    rows: List[Dict[str, Any]] = []
    for fp in files:
        try:
            rows.append(_extract_row(fp))
        except Exception as e:
            print(f"[WARN] Skipping {fp}: {e}")
    return rows

# -------------------- Google Sheets via YAML creds --------------------

def load_credentials_from_yaml(file_path: str | Path) -> Dict[str, Any]:
    with open(file_path, "r") as yaml_file:
        config = yaml.safe_load(yaml_file)
    return config["google_sheets"]

def get_gspread_client_from_yaml(path_to_yaml: str | Path) -> gspread.Client:
    creds_data = load_credentials_from_yaml(path_to_yaml)

    # Define scopes (Sheets + Drive)
    SCOPES = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]

    # Create credentials and client
    credentials = Credentials.from_service_account_info(creds_data, scopes=SCOPES)
    client = gspread.authorize(credentials)
    return client

def open_spreadsheet_by_id(spreadsheet_id: str) -> gspread.Spreadsheet:
    if not PATHS or "config" not in PATHS:
        raise RuntimeError(
            "PATHS['config'] not available. Make sure your repo exposes PATHS with a 'config' YAML path."
        )
    client = get_gspread_client_from_yaml(PATHS["config"])
    return client.open_by_key(spreadsheet_id)

def upsert_worksheet(sh: gspread.Spreadsheet, worksheet_name: str, ncols: int) -> gspread.Worksheet:
    try:
        return sh.worksheet(worksheet_name)
    except gspread.exceptions.WorksheetNotFound:
        return sh.add_worksheet(title=worksheet_name, rows="100", cols=str(ncols))

def write_rows_to_sheet_by_id(rows: List[Dict[str, Any]], spreadsheet_id: str, worksheet_name: str):
    sh = open_spreadsheet_by_id(spreadsheet_id)
    ws = upsert_worksheet(sh, worksheet_name, len(COLUMNS))

    ws.clear()
    ws.append_row(COLUMNS)

    values = [[str(r.get(col, "")) for col in COLUMNS] for r in rows]
    chunk = 500
    for i in range(0, len(values), chunk):
        ws.append_rows(values[i:i+chunk])

# -------------------- CSV (optional) --------------------

def write_csv(rows: List[Dict[str, Any]], csv_out: str) -> None:
    p = Path(csv_out)
    p.parent.mkdir(parents=True, exist_ok=True)
    import csv
    with p.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLUMNS})

# -------------------- Public entrypoint --------------------

def run_catalog(
    root: str | Path = ROOT_DIR,
    spreadsheet_id: str = SPREADSHEET_ID,
    worksheet: str = WORKSHEET_NAME,
    csv_out: Optional[str] = CSV_OUT,
    pattern: str = GLOB_PATTERN,
) -> int:
    rows = build_rows(root, pattern)
    if csv_out:
        write_csv(rows, csv_out)
    write_rows_to_sheet_by_id(rows, spreadsheet_id, worksheet)
    print(f"Done. Wrote {len(rows)} rows to spreadsheet ID '{spreadsheet_id}' / worksheet '{worksheet}'")
    return len(rows)

# -------------------- VS Code: just press Run --------------------
if __name__ == "__main__":
    run_catalog()
