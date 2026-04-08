# Competitor Review Scraper

> Scraped Trustpilot Reviews aller Competitors und extrahiert Pain Points, Differenzierungs-Chancen und Markt-Insights. Negative Competitor-Reviews sind Gold für eigene Angles.

## Problem
Wir brauchen echte Pain Points aus dem Matratzen-Markt — nicht nur von unseren eigenen Kunden, sondern auch von unzufriedenen Kunden der Konkurrenz. Deren Probleme sind unsere Selling Points.

## Trigger
Beim Setup und regelmäßig (monatlich) für frische Markt-Insights.

## Workflow
1. Script liest `competitors/competitors.json`
2. Für jeden Competitor mit `trustpilot_url`: Reviews scrapen
3. Speichert Reviews getrennt pro Competitor
4. Generiert Markt-Übersicht mit Pain Points und Differenzierungs-Chancen

## Inputs
| Parameter | Typ | Pflicht | Default | Beschreibung |
|-----------|-----|---------|---------|--------------|
| --competitor | string | nein | alle | Einzelnen Competitor scrapen (Name) |
| --max-pages | int | nein | 5 | Max Seiten pro Competitor |
| --output-dir | string | nein | reviews/competitors/ | Output-Verzeichnis |

## Outputs
- `reviews/competitors/<name>/reviews_raw.json` — Reviews pro Competitor
- `reviews/competitors/<name>/summary.json` — Rating + Verteilung
- `reviews/competitors/market_overview.json` — Gesamt-Analyse aller Competitors

## market_overview.json Struktur
```json
{
  "scraped_at": "2026-04-08",
  "competitors": [
    {
      "name": "Simba Sleep",
      "rating": 4.2,
      "total_reviews": 15000,
      "scraped": 100,
      "top_complaints": ["Lieferung", "Härtegrad", "Haltbarkeit"],
      "top_praises": ["Komfort", "Preis-Leistung"]
    }
  ],
  "market_pain_points": ["...aggregierte Pain Points..."],
  "differentiation_opportunities": ["...wo Ora besser ist..."]
}
```

## Scripts
- `scripts/main.py` — Iteriert über Competitors, scraped Reviews, aggregiert Insights

## Ausführung
```bash
# Alle Competitors scrapen
python3 .claude/skills/competitor-review-scraper/scripts/main.py

# Nur einen Competitor
python3 .claude/skills/competitor-review-scraper/scripts/main.py --competitor "Simba Sleep"
```

## Dependencies
- Python 3, `requests`, `python-dotenv`
- `competitors/competitors.json` mit Trustpilot URLs

## Verbindungen
- Liest `competitors/competitors.json`
- Output wird von `angle-generator` genutzt (competitive Pain Points → eigene Angles)
- Nutzt gleiche Scraping-Logik wie `review-scraper`
