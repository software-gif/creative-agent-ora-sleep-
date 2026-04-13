# Competitor Ad Analysis

> Systematische Auswertung der Meta Ad Library über alle Competitors. Scraped Ads pro Brand, lässt Gemini 2.5 Flash Vision jedes Top-Creative analysieren, und synthetisiert daraus strategische Markt-Insights für Ora Sleep.

## Zweck

Der bestehende `ad-library-scraper` scraped eine einzelne Brand und berechnet Winner Scores. Das ist aber nur Rohmaterial — **was wir strategisch brauchen ist die Aggregation**: Welche Angles sind im Markt gesättigt? Welche Formate dominieren? Welche Whitespaces existieren für Ora? Wo können wir differenzieren?

Dieser Skill:
1. Läuft sequenziell durch alle `competitors.json` Einträge
2. Scraped jede Brand via Apify (reuse von `ad-library-scraper`)
3. Lässt Gemini die Top-Creatives jeder Brand via Vision einzeln analysieren (Angle, Style, Tone, Offer, Hook)
4. Aggregiert zu einem strukturierten Marktbild
5. Generiert einen Markt-Report mit konkreten Differenzierungs-Empfehlungen für Ora

## Input

Liest automatisch:
- `competitors/competitors.json` — Liste der Competitors (Name, Market, Page ID)
- `branding/brand.json` — Ora Produktdaten, Pricing (für Positionierungs-Vergleich)
- `branding/brand_guidelines.json` — Brand Voice (für Differenzierungs-Vorschläge)
- `angles/angles.json` — Bestehende Ora Angles (für Oversaturated/Gap Analyse)

**Wichtig — Facebook Page IDs:**
Die meisten Einträge in `competitors.json` haben aktuell `facebook_page_id: null`. Der Skill überspringt diese mit Warning. So findest du die IDs:

1. Gehe auf https://www.facebook.com/ads/library (oder DE / CH Domain)
2. Wähle Country = Switzerland, Ad Category = All
3. Suche nach Brand-Name
4. Wenn Ads gefunden: klick auf die Brand oben → URL enthält `view_all_page_id=XXXXXXXXX`
5. Alternativ: https://findmyfbid.com/ mit der FB Page URL
6. Trage Page ID in `competitors.json` ein

## Output

Alles unter `competitors/analysis/`:

- **`market_insights.json`** — Strukturierte Daten zum Weiterverarbeiten:
  - `oversaturated_angles` — was alle machen
  - `underexploited_angles` — Gaps für Ora
  - `format_distribution` — Image vs Video vs Carousel je Brand
  - `copy_themes` — wiederkehrende Hooks, Pricing-Tactics
  - `ora_differentiation` — 3-5 konkrete Empfehlungen
  - `per_competitor` — Per-Brand-Breakdown
- **`market_report.md`** — Leseoptimierter Report für Sandro/Harun
- **`ads_by_brand/<slug>_winners.json`** — Top 10 Winner pro Brand mit Vision-Analyse

Zusätzlich pro Competitor (via bestehender Scraper-Logik):
- `competitors/<slug>/ads_raw.json`
- `competitors/<slug>/ads_analyzed.json`
- `competitors/<slug>/assets/*.jpg`

## Flags

| Flag | Default | Beschreibung |
|------|---------|--------------|
| `--max-ads-per-brand` | 30 | Maximale Ads pro Competitor-Scrape |
| `--only "<Name>"` | alle | Nur einen Competitor neu scrapen |
| `--skip-scrape` | false | Cached Daten nutzen, nur Analyse neu laufen lassen |
| `--top-n` | 5 | Wie viele Top-Ads pro Brand via Vision analysiert werden |

## Ausführung

```bash
cd "ora-sleep/creative generator"

# Vollständiger Run — alle Competitors, 30 Ads je Brand, Top 5 via Vision
python3 .claude/skills/competitor-ad-analysis/scripts/main.py

# Nur Simba neu scrapen
python3 .claude/skills/competitor-ad-analysis/scripts/main.py --only "Simba Sleep"

# Analyse neu ohne erneuten Apify-Call (spart Credits)
python3 .claude/skills/competitor-ad-analysis/scripts/main.py --skip-scrape

# Tiefere Vision-Analyse (mehr Ads = bessere Insights, mehr Kosten)
python3 .claude/skills/competitor-ad-analysis/scripts/main.py --top-n 10
```

## Kosten

- **Apify:** ~0.01-0.05 USD pro Competitor (abhängig von Ad-Anzahl)
- **Gemini Vision:** ~0.001 USD pro analysiertem Ad → bei 4 Brands × 5 Top-Ads = ~0.02 USD
- **Gemini Text (Synthese):** ~0.001 USD
- **Total pro Full Run:** ~0.10-0.25 USD

Setze das in Relation: ein einziger Sandro-Zoom-Call zur Competitor-Recherche kostet mehr Zeit als 20 Runs dieses Skills.

## Trigger

- **Monatlich** als Routine-Refresh
- **Bei neuen Competitors** in `competitors.json`
- **Vor einem Creative-Sprint** als strategischer Input für den Angle-Generator
- **Nach großen Competitor-Launches** (neuer Flagship, großer Sale)

## Verbindungen

- Nutzt `ad-library-scraper/scripts/main.py` als Building-Block (import via sys.path)
- Feeds `angle-generator` — die `oversaturated_angles` und `underexploited_angles` sollten im nächsten Angle-Generator-Run als Prior berücksichtigt werden
- Feeds `briefing-agent` — die Markt-Insights können als zusätzlicher Kontext mitgegeben werden
- Outputs werden nicht automatisch in Supabase geschrieben — der Report wird von Menschen gelesen, nicht vom Board gerendert

## Health Claims Guardrail

Der Skill selbst produziert keine Copy — aber die Vision-Analyse kann Competitor-Health-Claims erkennen. Diese werden in den Insights als "Risk Flags" markiert, damit wir wissen welche Claims andere Brands machen (und die wir explizit NICHT kopieren wollen).

## Scripts

- `scripts/main.py` — Orchestriert den gesamten Workflow.
