# Prompt Builder

> Generiert dynamisch Creative-Prompts aus Angles, Brand-Daten und Andromeda-Diversification-Logik. Baut JSON-Prompts die direkt an den Creative Producer übergeben werden können.

## Problem
Statische Prompt-Templates führen zu repetitiven Creatives. Wir brauchen einen dynamischen Builder, der aus dem Pool an Angles, Sub-Angles, Awareness-Stages und Formaten immer frische, diverse Prompt-Kombinationen generiert.

## Trigger
Wenn neue Creatives generiert werden sollen. User gibt Richtung vor (Angle, Produkt, Menge), der Builder macht den Rest.

## Workflow
1. User gibt an: Produkt, Angle (optional), Anzahl, Format
2. Script lädt: angles.json, brand.json, brand_guidelines.json
3. Builder wählt dynamisch:
   - Angle + Sub-Angle (rotierend, keine Wiederholung)
   - Awareness Stage (verteilt über Batch)
   - Creative Type (product_static / lifestyle Mix)
   - Visuellen Stil (on_brand / off_brand Variation)
4. Generiert JSON-Prompts kompatibel mit creative-producer
5. Output: Prompt-Datei ready für `creative-producer --prompts-file`

## Inputs
| Parameter | Typ | Pflicht | Default | Beschreibung |
|-----------|-----|---------|---------|--------------|
| --product | string | ja | - | Produkt-Handle aus brand.json |
| --angle | string | nein | random | Angle-ID oder "mix" für gemischte Batch |
| --count | int | nein | 6 | Anzahl Creatives |
| --format | string | nein | mix | "4:5", "9:16", "1:1" oder "mix" |
| --style | string | nein | mix | "on_brand", "off_brand" oder "mix" |
| --type | string | nein | mix | "product_static", "lifestyle" oder "mix" |
| --output | string | nein | auto | Output-Pfad für Prompts JSON |

## Dynamik-Prinzipien

### Angle-Rotation
- Bei `--angle mix`: Wählt aus allen verfügbaren Angles
- Verteilt gleichmäßig über Kern-Angles (Pain, Benefit, Proof)
- Mischt Skalierungs-Angles ein (Curiosity, Education, Story, Offer)
- Kein Angle wird doppelt verwendet bevor alle einmal dran waren

### Format-Verteilung
- Bei `--format mix`: Verteilt über 4:5, 9:16, 1:1
- Gewichtet: 40% 4:5 (Feed), 40% 9:16 (Story), 20% 1:1 (Square)

### Style-Mix
- Bei `--style mix`: 70% on_brand, 30% off_brand
- Off-Brand = experimentellere Farben, andere Schriften, mutigere Layouts

### Type-Mix
- Bei `--type mix`: 60% product_static, 40% lifestyle
- Lifestyle Szenen: Schlafzimmer, Bett, Person beim Schlafen/Aufwachen

### Headline-Generierung
- Wählt aus headline_variants des gewählten Angles
- Variiert Hook-Texte aus hook_variants
- Verwendet Data Points als Statistik-Headlines

## Outputs
- `creatives/<batch_id>_prompts.json` — JSON-Prompts ready für creative-producer
- Jeder Prompt enthält: meta, canvas, layout, product, text_overlays, generation_instructions

## Ausführung
```bash
# 6 gemischte Creatives für Matratze
python3 .claude/skills/prompt-builder/scripts/main.py --product ora-ultra-matratze --count 6

# 10 Pain-Angle Creatives im Feed-Format
python3 .claude/skills/prompt-builder/scripts/main.py --product ora-ultra-matratze --angle Problem/Pain --count 10 --format 4:5

# Wildes Mix-Batch
python3 .claude/skills/prompt-builder/scripts/main.py --product ora-ultra-matratze --count 20 --angle mix --format mix --style mix --type mix
```

## Diversifikations-Check
Vor der Generierung prüft der Builder:
- Sind mindestens 3 verschiedene Angles im Batch?
- Sind mindestens 2 verschiedene Formate dabei?
- Ist mindestens ein Lifestyle-Creative dabei?
- Sind die Headlines wirklich verschieden?

## Health Claims Guardrail
Der Builder filtert alle Headlines und Hooks gegen die Health Claims Blocklist aus angles.json.

## Scripts
- `scripts/main.py` — Dynamischer Prompt-Generator

## Dependencies
- Python 3 (nur stdlib)

## Verbindungen
- Liest `angles/angles.json` für Angle-Daten
- Liest `branding/brand.json` für Produkte und Benefits
- Liest `branding/brand_guidelines.json` für Farben und Fonts
- Output wird von `creative-producer` konsumiert
- Referenziert `meta-andromeda` Diversifikations-Logik
