# Competitor Cloner

> Klont Competitor-Ad-Konzepte mit eigenen Produkten und Benefits. Nimmt ein Competitor-Ad-Bild als Referenz und generiert eine eigene Version im gleichen Design-Stil.

## Problem
Competitor Ads manuell zu klonen ist zeitaufwändig: Design analysieren, in Canva nachbauen, Benefits anpassen, Produkt einsetzen. Dieser Skill automatisiert den Prozess: Competitor-Bild rein → eigene Version raus.

## Trigger
Wenn ein Competitor-Ad gefunden wird, das als Vorlage dienen soll. User gibt das Competitor-Bild und das gewünschte Produkt an.

## Workflow
1. User gibt Competitor-Ad-Bild (Pfad oder URL) + Produkt an
2. Claude analysiert das Competitor-Ad:
   - Design-Konzept (Layout, Farben, Style)
   - Welche Elemente vorhanden sind (Benefits, Headline, CTA etc.)
   - Was übernommen vs. ersetzt werden soll
3. Claude baut JSON-Prompt der das Design-Konzept mit eigenem Branding kombiniert:
   - Gleicher Layout-Stil und visuelle Ästhetik
   - Eigenes Produkt statt Competitor-Produkt
   - Eigene Benefits statt Competitor-Benefits
   - Brand-Werte aus brand.json
4. Script sendet Competitor-Bild als Style-Referenz + Produktbild an Gemini
5. Compositor fügt Logo, Social Proof etc. hinzu
6. Upload nach Supabase

## Inputs

### Vom User (pro Cloning-Auftrag)
| Parameter | Typ | Pflicht | Beschreibung |
|-----------|-----|---------|--------------|
| competitor_image | string | ja | Pfad zum Competitor-Ad-Bild (lokal oder URL) |
| product | string | ja | Produkt-Handle aus `branding/brand.json` |
| benefits | list | nein | 3 Benefits (Default: aus brand.json) |
| headline | string | nein | Eigene Headline. Wenn leer: Claude generiert passend zum Konzept |
| keep_headline | bool | nein | Wenn true: Competitor-Headline übersetzen/adaptieren statt neu generieren |
| color | string | nein | Produktfarbe |
| num_variants | int | nein | Anzahl Varianten (Default: 2) |

### Automatisch gelesen
- `branding/brand.json` — Benefits, Brand Values, Trust Signals
- `branding/brand_guidelines.json` — Fonts, Farben
- `products/images/<handle>/` — Produktbilder

## Outputs
- Geklonte Creatives → Supabase Storage + Board
- Lokales Backup in `creatives/<batch_id>/`

## Regeln

### Was wird geklont
- **Design-Konzept:** Layout-Stil, visuelle Ästhetik, Composition
- **Elemente-Anordnung:** Wo steht Headline, wo Benefits, wo Produkt
- **Stimmung:** Farbschema und visueller Ton (soweit passend zur Brand)

### Was wird ERSETZT
- **Produkt:** Immer eigenes Produkt, nie Competitor-Produkt
- **Benefits:** Immer eigene Benefits, nie Competitor-Benefits
- **Branding:** Eigenes Logo, Farben, Schriftart
- **Sprache:** Alles auf Deutsch
- **Trust Signals:** Eigene Trust Signals aus brand.json

### Was wird NICHT gemacht
- **Immer nur 1 Produkt** pro Creative (kein Mix)
- **Keine 1:1 Kopie** — das Design-Konzept inspiriert, aber eigenes Branding dominiert
- **Keine Competitor-Logos oder -Namen** im Output
- **Keine erfundenen Produktfeatures** — nur echte Benefits aus brand.json

## Gemini-Prompt-Strategie
Das Competitor-Bild wird als **Style-Referenz** an Gemini gesendet (nicht als Produkt-Quelle):
```
[Competitor-Bild] "Above is a reference ad design. Create a new ad INSPIRED by this layout
and visual style, but using the product image below and the following brand specifications..."
[Produktbild] "This is the actual product to feature in the ad..."
```

## Scripts
- `scripts/main.py` — Baut den Cloning-Prompt, nutzt creative-producer als Engine
- Competitor-Bild wird als zusätzlicher Input an Gemini gesendet

## Ausführung
Wird durch Claude gesteuert:
1. Claude analysiert Competitor-Ad (visuell, falls Bildverständnis verfügbar, sonst User-Beschreibung)
2. Claude baut JSON-Prompt mit Style-Referenz
3. Claude ruft Generation-Script auf

## Dependencies
- Alle Dependencies von `creative-producer`
- `branding/brand.json` + `brand_guidelines.json`
- Produktbilder in `products/images/`

## Verbindungen
- Nutzt `creative-producer` als Generation-Engine
- Liest `brand.json` für Benefits und Brand Values
- Kann mit `ad-library-scraper` kombiniert werden (Winner Ads als Input)
