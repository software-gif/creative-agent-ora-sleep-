#!/usr/bin/env python3
"""
briefing-agent — Generates Meta-optimized ad copy + briefing for existing creatives.

Reads creative rows from Supabase, downloads the image, loads brand voice and
angle context, calls Gemini 2.5 Flash with vision, and writes structured copy
back to the same rows.

Usage (run from creative-generator root):
  python3 .claude/skills/briefing-agent/scripts/main.py <creative_id> [<creative_id>...]

Env vars required (loaded from .env at creative-generator root):
  GEMINI_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""

import base64
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests


PROJECT_ROOT = Path(__file__).resolve().parents[4]  # creative generator/
BRANDING_DIR = PROJECT_ROOT / "branding"
ANGLES_DIR = PROJECT_ROOT / "angles"
ENV_PATH = PROJECT_ROOT / ".env"

TEXT_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{TEXT_MODEL}:generateContent"


# ---------------------------------------------------------------------------
# Env loading
# ---------------------------------------------------------------------------

def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    # Fallback to process env
    for key in ("GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"):
        if key not in env and key in os.environ:
            env[key] = os.environ[key]
    missing = [k for k in ("GEMINI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") if not env.get(k)]
    if missing:
        sys.exit(f"Error: missing env vars: {missing}")
    return env


# ---------------------------------------------------------------------------
# Supabase helpers
# ---------------------------------------------------------------------------

class SB:
    def __init__(self, env):
        self.url = env["SUPABASE_URL"].rstrip("/")
        self.key = env["SUPABASE_SERVICE_ROLE_KEY"]
        self.headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "Prefer": "return=representation",
        }

    def get_creative(self, creative_id):
        r = requests.get(
            f"{self.url}/rest/v1/creatives",
            headers=self.headers,
            params={"id": f"eq.{creative_id}", "select": "*"},
            timeout=15,
        )
        r.raise_for_status()
        rows = r.json()
        if not rows:
            raise ValueError(f"Creative not found: {creative_id}")
        return rows[0]

    def update_creative(self, creative_id, fields):
        r = requests.patch(
            f"{self.url}/rest/v1/creatives",
            headers=self.headers,
            params={"id": f"eq.{creative_id}"},
            json=fields,
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def download_image(self, storage_path):
        r = requests.get(
            f"{self.url}/storage/v1/object/public/creatives/{storage_path}",
            headers={"apikey": self.key, "Authorization": f"Bearer {self.key}"},
            timeout=60,
        )
        r.raise_for_status()
        return r.content


# ---------------------------------------------------------------------------
# Gemini call
# ---------------------------------------------------------------------------

def gemini_generate(api_key, system_prompt, user_prompt, image_bytes, image_mime):
    parts = [
        {"text": system_prompt},
        {"text": user_prompt},
        {"inline_data": {"mime_type": image_mime, "data": base64.b64encode(image_bytes).decode("utf-8")}},
    ]
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": 0.85,
            "topP": 0.95,
            "maxOutputTokens": 4096,
            "responseMimeType": "application/json",
        },
    }
    for attempt in range(3):
        try:
            r = requests.post(GEMINI_URL, params={"key": api_key}, json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            candidates = data.get("candidates", [])
            if not candidates:
                print(f"  empty candidates (attempt {attempt+1})")
                time.sleep(2)
                continue
            text = "".join(
                p.get("text", "")
                for p in candidates[0].get("content", {}).get("parts", [])
            ).strip()
            if text:
                return text
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status == 429:
                print(f"  rate limited, waiting {8*(attempt+1)}s")
                time.sleep(8 * (attempt + 1))
                continue
            print(f"  HTTP {status}: {e}")
            time.sleep(2)
        except Exception as e:
            print(f"  error: {e}")
            time.sleep(2)
    raise RuntimeError("Gemini call failed after 3 attempts")


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Du bist ein Senior Performance-Marketing-Texter für Ora Sleep, eine Schweizer D2C-Matratzenmarke. Dein Job: aus einem existierenden Static-Ad-Creative eine komplette Meta-Ad-Copy-Spec schreiben — Primary Text, 5 Headline-Varianten, Description, CTA, Briefing-Rationale, Target Audience.

KRITISCH — HEALTH CLAIMS GUARDRAIL:
Ora Sleep darf laut Kunden-Briefing keine Heilversprechungen machen. Ein Verstoß führt zur Meta-Account-Sperre.

VERBOTEN:
- "heilt Rückenschmerzen" / "garantiert besseren Schlaf" / "beseitigt Schlafstörungen"
- "klinisch getestet" / "medizinisch bewiesen" / "therapeutisch"
- Jegliche absoluten Versprechen über Schmerzlinderung oder Schlafqualität

ERLAUBT:
- "49% unserer Kunden berichten von weniger Schmerzen"
- "laut Kundenumfrage unter 108 Ora-Kundinnen und Kunden"
- "viele Ora-Kunden berichten" / "bei vielen Schlafenden"
- Du-Form, direkt, ehrlich, Swiss Understatement
- Trust Signals (Swiss Made, Testsieger, 10 Jahre Garantie) als Fakten

META-COPY-LIMITS (hart):
- primary_text: max 500 Zeichen, optimal ~125 damit nichts im Feed abgeschnitten wird
- headlines: 5 Varianten, JEDE max 40 Zeichen
- description: max 30 Zeichen (Meta Link Description)
- cta: EXAKT einer aus ["Jetzt kaufen", "Mehr erfahren", "Angebot sichern", "Mehr ansehen"]

OUTPUT: strict JSON, keine Markdown-Codefence, folgendes Schema:
{
  "primary_text": "...",
  "headlines": ["...", "...", "...", "...", "..."],
  "description": "...",
  "cta": "Jetzt kaufen",
  "briefing_rationale": "...",
  "target_audience": "..."
}
"""


def build_user_prompt(creative, brand_guidelines, brand_data, angle_info):
    hook = creative.get("hook_text", "")
    angle = creative.get("angle", "")
    sub_angle = creative.get("sub_angle", "")
    fmt = creative.get("format", "")

    return f"""Analysiere das angehängte Creative-Bild und schreibe die Meta-Ad-Copy.

CREATIVE-KONTEXT:
- Angle: {angle}
- Sub-Angle: {sub_angle}
- Format: {fmt}
- Headline im Bild: "{hook}"

BRAND VOICE (aus brand_guidelines.json):
{json.dumps(brand_guidelines.get('tone_of_voice', {}), ensure_ascii=False, indent=2)}

ANGLE-KONTEXT (aus angles.json):
{json.dumps(angle_info, ensure_ascii=False, indent=2)}

PRODUKT-FAKTEN (aus brand.json):
{json.dumps({
    'products': brand_data.get('products', []),
    'trust_signals': brand_data.get('trust_signals', []),
    'social_proof': brand_data.get('social_proof', {})
}, ensure_ascii=False, indent=2)}

AUFGABE:
1. Lies das Bild — welche visuelle Metapher wird genutzt? Was ist im Vordergrund? Welcher Ton strahlt das Bild aus?
2. Lies die Headline im Bild — welche Message ist schon gesetzt?
3. Schreib einen Primary Text (~125 Zeichen), der die Bild-Headline ERGÄNZT, nicht wiederholt. Der Primary Text ist die längere Story neben dem Bild im Feed.
4. Schreib 5 Headline-Varianten (je ≤40 Zeichen) für Meta. Variation ist kritisch — nicht dieselbe Idee 5×. Denke an: direkter Hook, Frage, Zahl, Testimonial-Fragment, Kontrast.
5. Description (≤30 Zeichen): eine knappe Zusatz-Message fürs Link Preview.
6. CTA: wähle einen aus der Liste.
7. Briefing Rationale (2-3 Sätze): Warum performt dieses Creative für diesen Angle? Wer ist die Zielgruppe? Worauf reagiert sie?
8. Target Audience (kurz, 1 Satz): Demografie + Trigger.

Halte dich an die Health-Claims-Guardrail. Schreib NUR das JSON, nichts drumherum."""


# ---------------------------------------------------------------------------
# Context loaders
# ---------------------------------------------------------------------------

def load_brand_context():
    brand_guidelines = {}
    brand_data = {}
    angles = []
    for name, path in [
        ("brand_guidelines", BRANDING_DIR / "brand_guidelines.json"),
        ("brand", BRANDING_DIR / "brand.json"),
    ]:
        if path.exists():
            with open(path) as f:
                data = json.load(f)
                if name == "brand_guidelines":
                    brand_guidelines = data
                else:
                    brand_data = data
    angles_path = ANGLES_DIR / "angles.json"
    if angles_path.exists():
        with open(angles_path) as f:
            data = json.load(f)
            angles = data if isinstance(data, list) else data.get("angles", [])
    return brand_guidelines, brand_data, angles


def find_angle_info(angles, angle_key):
    if not angle_key:
        return {}
    for a in angles:
        key = a.get("key") or a.get("slug") or a.get("id")
        if key == angle_key:
            return a
    return {"note": f"Angle '{angle_key}' nicht in angles.json gefunden"}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process_creative(sb, env, creative_id, brand_guidelines, brand_data, angles):
    print(f"\n→ {creative_id}")
    creative = sb.get_creative(creative_id)
    storage_path = creative.get("storage_path")
    if not storage_path:
        print(f"  skip: no storage_path")
        return False

    print(f"  angle: {creative.get('angle')} / {creative.get('sub_angle')}")
    print(f"  hook:  {creative.get('hook_text')}")
    print(f"  format: {creative.get('format')}")

    image_bytes = sb.download_image(storage_path)
    mime = "image/png" if storage_path.lower().endswith(".png") else "image/jpeg"
    print(f"  image: {len(image_bytes)/1024:.0f} KB")

    angle_info = find_angle_info(angles, creative.get("angle"))
    user_prompt = build_user_prompt(creative, brand_guidelines, brand_data, angle_info)

    print(f"  calling gemini-2.5-flash...")
    raw = gemini_generate(env["GEMINI_API_KEY"], SYSTEM_PROMPT, user_prompt, image_bytes, mime)

    # Strip any accidental markdown fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"  ✗ JSON parse failed: {e}")
        print(f"    raw: {raw[:300]}")
        return False

    # Validate
    for field in ("primary_text", "headlines", "description", "cta", "briefing_rationale", "target_audience"):
        if field not in parsed:
            print(f"  ✗ missing field: {field}")
            return False

    headlines = parsed["headlines"]
    if not isinstance(headlines, list) or len(headlines) < 3:
        print(f"  ✗ headlines must be a list of ≥3")
        return False

    # Hard clip to Meta limits (safety net in case Gemini ignored)
    parsed["primary_text"] = parsed["primary_text"][:500]
    parsed["headlines"] = [h[:40] for h in headlines[:5]]
    parsed["description"] = parsed["description"][:30]
    parsed["copy_generated_at"] = datetime.now(timezone.utc).isoformat()

    sb.update_creative(creative_id, parsed)

    print(f"  ✓ primary:   {parsed['primary_text'][:70]}...")
    print(f"  ✓ headlines: {len(parsed['headlines'])} variants")
    for i, h in enumerate(parsed["headlines"], 1):
        print(f"      {i}. {h}")
    print(f"  ✓ cta:       {parsed['cta']}")
    print(f"  ✓ target:    {parsed['target_audience']}")
    return True


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python3 main.py <creative_id> [<creative_id>...]")

    env = load_env()
    sb = SB(env)
    brand_guidelines, brand_data, angles = load_brand_context()
    print(f"Loaded: {len(brand_guidelines)} guideline sections, {len(angles)} angles")

    ok = 0
    fail = 0
    for cid in sys.argv[1:]:
        try:
            if process_creative(sb, env, cid, brand_guidelines, brand_data, angles):
                ok += 1
            else:
                fail += 1
        except Exception as e:
            print(f"  ✗ exception: {e}")
            fail += 1

    print(f"\nDone. {ok} ok, {fail} failed.")
    sys.exit(0 if fail == 0 else 1)


if __name__ == "__main__":
    main()
