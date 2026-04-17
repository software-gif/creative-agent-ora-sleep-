# Freisteller

> Entfernt den Hintergrund von Produktbildern und erzeugt transparente PNGs. Nutzt FAL BiRefNet — state-of-the-art Segmentation, ~$0.01 pro Bild, ~3 Sek.

## Zweck

Für Static Ads, Packshots und Compositing brauchen wir Produkte auf transparentem Hintergrund. Manuelles Freistellen in Photoshop ist zeitaufwändig und fehleranfällig. BiRefNet liefert Sub-Pixel-Kanten und versteht komplexe Objekte (Matratzen, Textilien, Schaum).

## Aufruf

```bash
cd "ora-sleep/creative generator"

# Einzelbild
python3 .claude/skills/freisteller/scripts/main.py path/to/image.jpg

# Ganzer Ordner
python3 .claude/skills/freisteller/scripts/main.py products/images/ora-ultra-matratze/

# Bestimmte Datei + Custom Output-Pfad
python3 .claude/skills/freisteller/scripts/main.py input.jpg -o output_cutout.png
```

## Output

Speichert `*_cutout.png` (RGBA, transparenter Hintergrund) neben dem Original.
- `ora-ultra-matratze-0.jpg` → `ora-ultra-matratze-0_cutout.png`

## Kosten

~$0.01 pro Bild via FAL BiRefNet. Bei 15 Produktbildern = $0.15.

## Env

Benötigt `FAL_KEY` in `.env` (bei uns im `ai-visuals/.env`).

## Tipps

- **Beste Ergebnisse:** Produkt auf solidem oder einfachem Hintergrund
- **Akzeptable Ergebnisse:** Produkt in Lifestyle-Setting (BiRefNet segmentiert das salionteste Objekt)
- **Schwierig:** Produkt ist nur ein kleiner Teil eines komplexen Bildes (Text-Overlays, Infografiken)
