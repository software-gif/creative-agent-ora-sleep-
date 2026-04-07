# Creative Producer

> Generiert Static Ads via Gemini 3.1 Flash Image Generation basierend auf Ad Angles, Brand Guidelines und Produktbildern. Inkl. Multi-Layer Compositor (Logo, Social Proof, Payment Icons).

## Problem
Manuell Static Ads zu erstellen ist zeitaufwändig und erfordert Design-Expertise. Der Creative Producer automatisiert die Generierung von brand-konformen Static Ads basierend auf der Andromeda-Diversification-Logik.

## Trigger
Nachdem Prompts (von sales-event-producer, competitor-cloner oder manuell) erstellt wurden.

## Workflow
1. JSON-Prompts werden übergeben (von sales-event-producer, competitor-cloner oder manuell)
2. Script sendet JSON-Prompt + Produktbild an Gemini 3.1 Flash
3. Multi-Layer Compositor fügt Overlays hinzu (Logo, Social Proof, Payment Icons, Farbvarianten)
4. Upload nach Supabase Storage + DB Update
5. Creatives erscheinen live im Board

## Inputs
- JSON-Prompts-Datei (von anderen Skills oder manuell erstellt)
- `--brand-id` (optional, auto-detected)
- Produktbilder in `products/images/<handle>/`
- Overlay-Assets in `branding/`:
  - `logo_dark.png` / `logo_white.png` — Brand Logo
  - `social_proof.png` — Trust Badge (optional)
  - `payment_icons.png` — Payment Methods (optional)
  - `color_variants.png` — Farbpunkte (optional)

## Outputs
- Generierte Creatives → Supabase Storage `creatives/{brand_id}/{batch_id}/`
- DB-Einträge in `creatives` Tabelle mit `status='done'`, `image_url`, `storage_path`
- Lokales Backup in `creatives/<batch_id>/`
- `manifest.json` pro Batch

## Formate
- **4:5** (1536×1920) — Feed
- **9:16** (1080×1920) — Story (mit 1:1 Safe Zone)

## Multi-Layer Compositor
Nach der Gemini-Generierung werden folgende Overlays automatisch composited (wenn die Dateien existieren):

1. **Logo** — Auto-Detect: dunkles Logo auf hellem Hintergrund, weißes auf dunklem
2. **Social Proof** — Trust Badge (z.B. "⭐ 4.8 | 500+ zufriedene Kunden")
3. **Payment Icons** — PayPal, Visa, Mastercard etc.
4. **Farbvarianten** — Kleine Kreise mit verfügbaren Farben

Alle Overlays sind optional — wenn die PNG-Datei nicht existiert, wird sie übersprungen.

## Scripts
- `scripts/main.py` — Orchestrierung: Gemini API Call, Compositor, Supabase Upload
- `scripts/prompt_schema.json` — JSON-Prompt-Schema (Single Source of Truth)

## Ausführung
```bash
# Direkt mit Prompts-Datei
python3 .claude/skills/creative-producer/scripts/main.py --prompts-file creatives/prompts.json

# Brand-ID wird automatisch aus DB gelesen (nur 1 Brand)
```

## Dependencies
- Python 3
- `requests` (pip)
- `python-dotenv` (pip)
- `Pillow` (pip) — für Compositor
- Gemini API Key in `.env` (`GEMINI_API_KEY`)
- Supabase Credentials in `.env`

## Wichtige Regeln für Bild-Prompts

### Produkt NICHT in negativen Szenen
Bei Szenen die etwas Negatives kommunizieren darf das beworbene Produkt NIEMALS im Bild erscheinen. `scene_type: "negative"` blockt automatisch das Produktbild.

### Nur echte Produktvarianten
Zeige nur Produktfarben die in `brand.json` existieren.

### Safe Zone (9:16 Format)
Hauptcontent (Produkt, Headline, Benefits, CTA) im mittleren 1:1 Bereich. Logo oben, Social Proof unten — außerhalb der 1:1 Zone.

### Schriftart
Poppins Bold für Headlines, Poppins Medium für Body. Immer deutsch.

## Verbindungen
- Wird von `sales-event-producer` und `competitor-cloner` als Engine genutzt
- Liest Output von `angle-generator`, `product-scraper`, `ad-library-scraper`
- Referenziert `meta-andromeda` Knowledge
- Liest `branding/brand_guidelines.json`
