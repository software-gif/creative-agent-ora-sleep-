# Creative Producer

> Generiert Static Ads via Gemini Image Generation basierend auf Ad Angles, Brand Guidelines und Produktbildern. Inkl. Multi-Layer Compositor (Logo, Social Proof, Payment Icons).

## Problem
Manuell Static Ads zu erstellen ist zeitaufwändig und erfordert Design-Expertise. Der Creative Producer automatisiert die Generierung von hochdiversen Static Ads basierend auf der Andromeda-Diversification-Logik.

## Ora Sleep Creative Philosophy
- **MAXIMALE DIVERSITY** — Kein festes Template. Jedes Creative soll anders aussehen.
- **Performance > Brand** — Keine starren CI-Vorgaben. Verschiedene Schriften, Farben, Layouts testen.
- **Mal mit Logo, mal ohne. Mal Text-heavy, mal minimal.**
- **Top-Performer bei Ora sind die simpelsten Creatives** — Nicht overdesignen.
- **KEINE Health Claims** — Niemals "heilt", "garantiert", "medizinisch bewiesen". Nur "Kunden berichten", "laut Umfrage", "verbessert".

## Trigger
Nachdem Prompts (von sales-event-producer, competitor-cloner, angle-generator oder manuell) erstellt wurden.

## Workflow
1. JSON-Prompts werden übergeben (von anderen Skills oder manuell)
2. Script sendet JSON-Prompt + Produktbild an Gemini
3. Multi-Layer Compositor fügt Overlays hinzu (Logo, Social Proof, Payment Icons)
4. Upload nach Supabase Storage + DB Update
5. Creatives erscheinen live im Board

## Inputs
- JSON-Prompts-Datei (von anderen Skills oder manuell erstellt)
- `--brand-id` (optional, auto-detected)
- Produktbilder in `products/images/<handle>/`
- Overlay-Assets in `branding/` (alle optional)

## Outputs
- Generierte Creatives → Supabase Storage `creatives/{brand_id}/{batch_id}/`
- DB-Einträge in `creatives` Tabelle
- Lokales Backup in `creatives/<batch_id>/`

## Formate
- **4:5** (1440×1800) — Feed
- **9:16** (1080×1920) — Story
- **1:1** (1440×1440) — Square

## Angles (aus Kundenfeedback-Studie, 108 Antworten)
Verfügbare Angles in `angles/angles.json`:
- **Einschlafzeit**: Von 30 auf 5 Min (60% unter 10 Min)
- **Rückenschmerzen**: 49% deutlich verbessert, 8% verschwunden
- **Schwitzen**: 44% "viel besser", 72% insgesamt verbessert
- **Morgen-Feeling**: Von 5.4 auf 8.6/10
- **Sofortige Wirkung**: 50% spüren Unterschied in 7 Tagen
- **NPS/Trust**: 8.6 NPS, 66% Promoters
- **Partner-Schlaf**: Weniger Störungen zu zweit
- **Swiss Made**: Schweizer Qualität
- **Wiederkäufer**: Kunden kaufen 2. Matratze
- **Freude aufs Bett**: Emotionale Bindung

## Health Claims Guardrail
⚠️ NIEMALS Heilversprechungen:
- ❌ "heilt Rückenschmerzen"
- ❌ "medizinisch bewiesen"
- ❌ "garantiert besserer Schlaf"
- ✅ "49% unserer Kunden berichten von Verbesserung"
- ✅ "Laut Kundenumfrage..."
- ✅ "Viele Kunden schlafen besser"

## Creative-Typen
- **product_static**: Freisteller + Headlines/Icons/Daten
- **lifestyle**: Schlafzimmer-Settings, Personen im Bett, gemütliche Szenen
- **data_driven**: Statistiken/Zahlen aus der Studie im Fokus
- **testimonial**: Echte Kundenzitate als Creative

## Scripts
- `scripts/main.py` — Orchestrierung: Gemini API Call, Compositor, Supabase Upload
- `scripts/prompt_schema.json` — JSON-Prompt-Schema

## Ausführung
```bash
python3 .claude/skills/creative-producer/scripts/main.py --prompts-file creatives/prompts.json
```

## Dependencies
- Python 3, `requests`, `python-dotenv`, `Pillow`
- Gemini API Key in `.env`
- Supabase Credentials in `.env`

## Wichtige Regeln für Bild-Prompts

### Produkt NICHT in negativen Szenen
Bei negativen Szenen darf das Produkt NICHT im Bild erscheinen.

### Diversity-First
Jedes Creative soll sich vom vorherigen unterscheiden — andere Schrift, anderes Layout, andere Farbgebung, anderer Stil.

### Safe Zone (9:16 Format)
Hauptcontent im mittleren 1:1 Bereich. Logo oben, Social Proof unten.

### Schriftart
Jost Bold als Standard, aber bewusst auch andere Schriften nutzen für Diversity.

## Verbindungen
- Wird von `sales-event-producer` und `competitor-cloner` als Engine genutzt
- Liest Angles aus `angles/angles.json`
- Referenziert `meta-andromeda` Knowledge
- Liest `branding/brand_guidelines.json`
