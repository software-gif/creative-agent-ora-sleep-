# Angle Generator

> Generiert Ad Angles und Sub-Angles basierend auf Reviews, Kundenfeedback-Studien und Winner-Analyse. Claude analysiert die Daten direkt — kein externes LLM nötig.

## Problem
Manuell Ad Angles aus hunderten Reviews abzuleiten ist zeitaufwändig und subjektiv. Der Angle Generator bereitet die Daten auf und Claude leitet daraus spezifische, authentische Angles ab — basierend auf der Meta Andromeda Diversification-Logik.

## Ora Sleep Kontext
- **Kundenfeedback-Studie** mit 108 Antworten bereits ausgewertet in `angles/angles.json`
- **Stärkste Datenpunkte:**
  - Einschlafzeit: 60% jetzt unter 10 Minuten (vorher 32%)
  - Morgen-Feeling: Von 5.4 auf 8.6/10
  - Beschwerden: 49% deutlich verbessert, 8% verschwunden
  - Temperatur: 72% verbessert
  - NPS: 8.6 (66% Promoters)
- **Health Claims Guardrail:** Nur "Kunden berichten", "laut Umfrage" — keine Heilversprechungen

## Trigger
Nachdem Review Scraper und Ad Library Scraper gelaufen sind, oder wenn neue Kundendaten vorliegen.

## Workflow
1. `scripts/main.py` liest Reviews, Winner-Ads und Brand-Daten
2. Script erstellt eine strukturierte Zusammenfassung (`angles/review_summary.json`)
3. Claude analysiert die Daten und aktualisiert `angles/angles.json`

## Inputs
| Parameter    | Typ    | Pflicht | Default  | Beschreibung                     |
|--------------|--------|---------|----------|----------------------------------|
| --output-dir | string | nein    | angles/  | Verzeichnis für Output           |

Liest automatisch:
- `reviews/reviews_raw.json` — Kundenstimmen
- `angles/angles.json` — Bestehende Angles (aus Studie)
- `brand.json` — Brand-Kontext

## Outputs
- `angles/review_summary.json` — Aufbereitete Daten für Analyse
- `angles/angles.json` — Alle generierten Angles mit Sub-Angles und Review-Belegen

## Angle-Kategorien (7 total)
- **Core (3):** Problem/Pain 🔥, Benefit ✨, Proof ✅
- **Scaling (4):** Curiosity 🔮, Education 📚, Story 💜, Offer 🏷️
- Pro Angle: 5-8 spezifische Sub-Angles, belegt durch echte Reviews/Daten

## Bestehende Angles (aus Studie)
1. Schneller einschlafen (Benefit)
2. Rückenschmerzen verschwunden (Pain)
3. Nie wieder Schwitzen (Pain)
4. Morgens wie neugeboren (Benefit)
5. Sofortige Wirkung (Proof)
6. Kunden empfehlen weiter (Proof)
7. Besser schlafen zu zweit (Benefit)
8. Swiss Made Qualität (Proof)
9. Wiederkäufer (Story)
10. Freude aufs Bett (Story)

## Scripts
- `scripts/main.py` — Liest alle Datenquellen, bereitet Zusammenfassung auf.

## Ausführung
```bash
python3 .claude/skills/angle-generator/scripts/main.py
```

## Dependencies
- Python 3 (nur stdlib)

## Verbindungen
- Liest Output von `review-scraper` und `ad-library-scraper`
- Referenziert `meta-andromeda` Knowledge für Angle-Hierarchie
- Output wird von `creative-producer` Skill verwendet
