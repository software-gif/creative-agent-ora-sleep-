#!/usr/bin/env python3
"""
sync_to_board.py — Seed / refresh angles + competitors tables in Supabase.

Reads:
  - angles/angles.json           → angles + angle_variants
  - competitors/competitors.json → competitors

Run once after migration 003 to backfill. Rerun any time to refresh —
upserts by (brand_id, key) for angles and (brand_id, slug) for competitors.

Usage:
  cd "creative generator"
  python3 scripts/sync_to_board.py
  python3 scripts/sync_to_board.py --only angles
  python3 scripts/sync_to_board.py --only competitors
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[1]  # creative generator/
ANGLES_JSON = PROJECT_ROOT / "angles" / "angles.json"
COMPETITORS_JSON = PROJECT_ROOT / "competitors" / "competitors.json"
ENV_PATH = PROJECT_ROOT / ".env"


def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "BRAND_ID"):
        if k not in env and k in os.environ:
            env[k] = os.environ[k]
    missing = [k for k in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "BRAND_ID") if not env.get(k)]
    if missing:
        sys.exit(f"Error: missing env vars: {missing}")
    return env


def slugify(s):
    s = s.lower()
    s = s.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


class SB:
    def __init__(self, env):
        self.url = env["SUPABASE_URL"].rstrip("/")
        self.key = env["SUPABASE_SERVICE_ROLE_KEY"]
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation,resolution=merge-duplicates",
        }

    def upsert(self, table, rows, on_conflict):
        if not rows:
            return []
        r = requests.post(
            f"{self.url}/rest/v1/{table}",
            headers=self.headers,
            params={"on_conflict": on_conflict},
            json=rows,
            timeout=30,
        )
        if not r.ok:
            print(f"  ✗ upsert {table} failed: {r.status_code} {r.text[:300]}")
            r.raise_for_status()
        return r.json()

    def delete(self, table, params):
        r = requests.delete(
            f"{self.url}/rest/v1/{table}",
            headers=self.headers,
            params=params,
            timeout=15,
        )
        if not r.ok:
            print(f"  ✗ delete {table} failed: {r.status_code} {r.text[:300]}")
            r.raise_for_status()


# ---------------------------------------------------------------------------
# Angles
# ---------------------------------------------------------------------------

def sync_angles(sb, brand_id):
    if not ANGLES_JSON.exists():
        print(f"  ✗ {ANGLES_JSON} not found — skipping angles")
        return 0, 0

    data = json.loads(ANGLES_JSON.read_text())
    angles = data if isinstance(data, list) else data.get("angles", [])
    if not angles:
        print("  (no angles in json)")
        return 0, 0

    print(f"Angles: syncing {len(angles)} rows…")

    # Upsert angles (one row each)
    angle_rows = []
    for i, a in enumerate(angles):
        key = a.get("id") or a.get("key") or slugify(a.get("name", f"angle-{i}"))
        angle_rows.append({
            "brand_id": brand_id,
            "key": key,
            "name": a.get("name", key),
            "type": a.get("type", "Unknown"),
            "data_point": a.get("data_point", ""),
            "priority": a.get("priority", i),
            "status": "active",
        })

    inserted = sb.upsert("angles", angle_rows, on_conflict="brand_id,key")
    print(f"  ✓ {len(inserted)} angle rows upserted")

    # Build key → id map from the upsert response
    key_to_id = {row["key"]: row["id"] for row in inserted}

    # Wipe existing variants for these angles (simplest way to keep variants in sync
    # without per-row diff). Safe because the child table has no external FKs.
    angle_ids = list(key_to_id.values())
    if angle_ids:
        # Delete via "id=in.(...)" — Supabase supports filter syntax
        sb.delete("angle_variants", {
            "angle_id": f"in.({','.join(angle_ids)})"
        })

    # Insert fresh variants
    variant_rows = []
    for a in angles:
        key = a.get("id") or a.get("key") or slugify(a.get("name", ""))
        angle_id = key_to_id.get(key)
        if not angle_id:
            continue
        for order, h in enumerate(a.get("headline_variants", []) or []):
            variant_rows.append({
                "angle_id": angle_id,
                "variant_type": "headline",
                "content": h,
                "display_order": order,
                "status": "active",
            })
        for order, h in enumerate(a.get("hook_variants", []) or []):
            variant_rows.append({
                "angle_id": angle_id,
                "variant_type": "hook",
                "content": h,
                "display_order": order,
                "status": "active",
            })

    if variant_rows:
        # Plain insert, not upsert (we wiped above)
        r = requests.post(
            f"{sb.url}/rest/v1/angle_variants",
            headers=sb.headers,
            json=variant_rows,
            timeout=30,
        )
        if not r.ok:
            print(f"  ✗ variant insert failed: {r.status_code} {r.text[:300]}")
            r.raise_for_status()
        print(f"  ✓ {len(variant_rows)} variant rows inserted")
    return len(inserted), len(variant_rows)


# ---------------------------------------------------------------------------
# Competitors
# ---------------------------------------------------------------------------

def sync_competitors(sb, brand_id):
    if not COMPETITORS_JSON.exists():
        print(f"  ✗ {COMPETITORS_JSON} not found — skipping competitors")
        return 0

    data = json.loads(COMPETITORS_JSON.read_text())
    active = data.get("competitors", []) or []
    excluded = data.get("excluded", []) or []

    print(f"Competitors: syncing {len(active)} active + {len(excluded)} excluded…")

    def make_row(c, status, notes_field="notes"):
        return {
            "brand_id": brand_id,
            "name": c.get("name", ""),
            "slug": slugify(c.get("name", "")),
            "market": c.get("market"),
            "website": c.get("website"),
            "facebook_page_id": c.get("facebook_page_id"),
            "trustpilot_url": c.get("trustpilot_url"),
            "status": status,
            "notes": c.get(notes_field),
        }

    rows = [make_row(c, "active") for c in active]
    rows += [make_row(c, "excluded", notes_field="reason") for c in excluded]
    rows = [r for r in rows if r["name"] and r["slug"]]
    inserted = sb.upsert("competitors", rows, on_conflict="brand_id,slug")
    print(f"  ✓ {len(inserted)} competitor rows upserted")
    return len(inserted)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["angles", "competitors"], default=None)
    args = parser.parse_args()

    env = load_env()
    sb = SB(env)
    brand_id = env["BRAND_ID"]

    print(f"Brand: {brand_id}")
    print()

    if args.only != "competitors":
        sync_angles(sb, brand_id)
    if args.only != "angles":
        sync_competitors(sb, brand_id)

    print("\nDone.")


if __name__ == "__main__":
    main()
