#!/usr/bin/env python3
"""Upload generated static-ads PNGs to Supabase so they appear on the Board.

Reads creative generator/.env for SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, BRAND_ID.
Uploads each PNG to the 'creatives' storage bucket and inserts a creatives row
with status='done' so the Board realtime channel picks it up immediately.

Usage:
  python3 scripts/upload_to_board.py <spec.json> <angle_key>=<slug> ...

Example:
  python3 scripts/upload_to_board.py \\
    brands/ora-sleep/static-ads/schwingen-garantie-ora-ultra-matratze/static-ad-spec.json \\
    swiss_quality=var-1-schwinger \\
    nps_trust=var-2-93-prozent \\
    rueckenschmerzen=var-3-ruecken
"""

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

import requests


CREATIVE_GEN_DIR = Path(__file__).resolve().parents[2] / "creative generator"
CREATIVE_GEN_ENV = CREATIVE_GEN_DIR / ".env"
BRIEFING_AGENT = CREATIVE_GEN_DIR / ".claude" / "skills" / "briefing-agent" / "scripts" / "main.py"


def load_env():
    env = {}
    for line in CREATIVE_GEN_ENV.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)

    spec_path = Path(sys.argv[1])
    mapping = dict(arg.split("=", 1) for arg in sys.argv[2:])

    env = load_env()
    url = env["SUPABASE_URL"].rstrip("/")
    key = env["SUPABASE_SERVICE_ROLE_KEY"]
    brand_id = env["BRAND_ID"]

    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    spec = json.loads(spec_path.read_text())
    output_dir = spec_path.parent
    output_name = spec["output_name"]
    aspect_ratio = spec.get("aspect_ratio", "4:5")
    batch_id = str(uuid.uuid4())

    print(f"Batch: {batch_id}")
    print(f"Brand: {brand_id}")

    variations = {v["slug"]: v for v in spec["variations"]}

    for angle_key, slug in mapping.items():
        if slug not in variations:
            print(f"  ✗ skip {slug}: not in spec")
            continue

        # Find local png
        png_files = sorted(output_dir.glob(f"{output_name}-{slug}_v*.png"))
        if not png_files:
            print(f"  ✗ skip {slug}: no png")
            continue
        png = png_files[-1]

        # Derive hook_text from the variation prompt (first headline line)
        hook_text = {
            "var-1-schwinger": "Diese Matratze übersteht zwei Schwinger.",
            "var-2-93-prozent": "93% schlafen besser mit Ora.",
            "var-3-ruecken": "Morgens ohne Rückenschmerzen aufstehen?",
        }.get(slug, "")

        # 1) Upload to storage
        storage_path = f"{brand_id}/{batch_id}/{png.name}"
        up_headers = {
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "image/png",
        }
        resp = requests.post(
            f"{url}/storage/v1/object/creatives/{storage_path}",
            headers=up_headers,
            data=png.read_bytes(),
            timeout=60,
        )
        if resp.status_code in (400, 409):
            up_headers["x-upsert"] = "true"
            resp = requests.post(
                f"{url}/storage/v1/object/creatives/{storage_path}",
                headers=up_headers,
                data=png.read_bytes(),
                timeout=60,
            )
        resp.raise_for_status()
        image_url = f"{url}/storage/v1/object/public/creatives/{storage_path}"
        print(f"  ✓ uploaded {png.name}")

        # 2) Insert row
        row = {
            "brand_id": brand_id,
            "batch_id": batch_id,
            "angle": angle_key,
            "sub_angle": "schwinger-garantie",
            "variant": 1,
            "format": aspect_ratio,
            "hook_text": hook_text,
            "status": "done",
            "is_saved": False,
            "storage_path": storage_path,
            "image_url": image_url,
        }
        r = requests.post(
            f"{url}/rest/v1/creatives",
            headers=headers,
            json=row,
            timeout=15,
        )
        r.raise_for_status()
        inserted = r.json()[0]
        creative_id = inserted["id"]
        print(f"  ✓ inserted creative {creative_id}")

        # 3) Auto-generate briefing + Meta copy via briefing-agent
        if BRIEFING_AGENT.exists():
            print(f"  → running briefing-agent...")
            result = subprocess.run(
                ["python3", str(BRIEFING_AGENT), creative_id],
                cwd=str(CREATIVE_GEN_DIR),
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                print(f"  ✓ briefing generated")
            else:
                print(f"  ⚠ briefing failed (non-fatal): {result.stderr.strip()[:200]}")

    print("\nDone — reload localhost:3000")


if __name__ == "__main__":
    main()
