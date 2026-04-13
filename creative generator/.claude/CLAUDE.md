# Ora Sleep — Creative Agent

## Projekt
Creative Agent für **Ora Sleep** (orasleep.ch) — Schweizer Matratzen-Brand. Generiert Performance-optimierte Static Ads via Gemini Image Generation + Supabase Board.

## Produkte
- **Ora Ultra Matratze** (ab CHF 899) — Hauptprodukt, Testsieger 2026
- **Ora Ultra Topper** (ab CHF 799) — Luxus-Upgrade

## ⚠️ HEALTH CLAIMS GUARDRAIL — HARTE REGEL
**NIEMALS Heilversprechungen in Creatives oder Prompts:**
- ❌ "heilt Rückenschmerzen" / "garantiert besseren Schlaf" / "medizinisch bewiesen"
- ❌ "beseitigt Schlafstörungen" / "therapeutisch" / "klinisch getestet"
- ✅ "49% unserer Kunden berichten von Verbesserung"
- ✅ "Laut Kundenumfrage schlafen 60% schneller ein"
- ✅ "Viele Kunden schlafen besser"

**Warum:** Meta Blacklist-Risiko. Kunden größte Sorge ist Account-Sperre.

## Creative Philosophy
1. **MAXIMALE DIVERSITY** — Kein festes Template. Jedes Creative anders.
2. **Performance > Brand** — Keine starren CI-Vorgaben. Simpelste Creatives performen oft am besten.
3. **Andromeda-Strategie** — Viele verschiedene Ansätze für verschiedene Zielgruppen-Segmente.
4. **Kein Zwang** — Mal mit Logo, mal ohne. Mal Text-heavy, mal minimal. Alles testen.

## Formate
Alle drei: **4:5** (Feed), **9:16** (Story), **1:1** (Square)

## Creative-Typen
- `product_static` — Freisteller + Headlines/Icons/Daten
- `lifestyle` — Schlafzimmer-Settings, Personen im Bett
- `data_driven` — Statistiken/Zahlen aus der Studie
- `testimonial` — Echte Kundenzitate

## Sprache & Ton
- Deutsch, du-Form
- Direkt, ehrlich, nicht übertrieben
- Keine Superlative ohne Datenbeleg
- Swiss Quality als Vertrauenssignal

## Datenquellen für Angles
- `angles/angles.json` — 10 Angles aus Kundenfeedback-Studie (108 Antworten)
- `branding/brand.json` — Produkte, Benefits, Trust Signals
- `branding/brand_guidelines.json` — Farben, Fonts, Layout

## Skills (in Reihenfolge der Nutzung)
1. **prompt-builder** — Dynamischer Prompt-Generator aus Angles + Brand-Daten + Andromeda-Diversification. Erstellt diverse, frische Prompt-Batches.
2. **creative-producer** — Gemini-basierte Ad-Generierung + Compositor + Supabase Upload
3. **angle-generator** — Angles aus Reviews/Daten ableiten
4. **briefing-agent** — Generiert Meta-optimierte Ad Copy + Briefing für ein bestehendes Creative (Gemini Vision)
5. **competitor-ad-analysis** — Systematische Meta Ad Library Auswertung über alle Competitors, synthetisiert strategische Markt-Insights. Schreibt automatisch in Supabase (`competitors`, `competitor_analyses`)
6. **sales-event-producer** — Sales-Event-Creatives (Black Friday etc.)
7. **competitor-cloner** — Competitor-Ads als Inspiration klonen
8. **competitor-review-scraper** — Trustpilot Reviews aller Competitors scrapen (Pain Points, Differenzierung)
9. **review-scraper** — Eigene Trustpilot Reviews scrapen
10. **product-scraper** — Shopify-Produktdaten scrapen
11. **ad-library-scraper** — Meta Ad Library scrapen (via Apify) — Building-Block, wird von competitor-ad-analysis importiert

## Board Pages (Display-Only)

Das Board unter `board/` ist die Display-Surface. Alle Trigger laufen über Claude Code selbst — **keine Buttons in der UI**, alles über Agent-Befehle. Neue Pages (Migration 003):

- **`/angles`** — liest `angles` + `angle_variants` Tabellen, gruppiert nach Type (Problem/Pain, Benefit, Proof, …), zeigt Data Point + Headline/Hook-Varianten + Creative-Counter pro Angle.
- **`/competitors`** — liest `competitors` + `competitor_analyses`, gruppiert nach Status (active/watching/excluded), Klick öffnet Detail-View mit Oversaturated/Whitespace/Differentiation-Cards aus der letzten Analyse.

### Agent Command Patterns

```
"Zeig mir Angle rueckenschmerzen"
→ Claude liest angle row + variants aus Supabase, präsentiert Summary im Chat

"Erstell ein Creative für einschlafzeit mit Feature-Showcase Referenz"
→ Claude ruft /static-ads skill, pullt angle-kontext (data_point + headline_variants + hook_variants)
  aus Supabase, verwendet als Grundlage für die Copy-Variationen

"Analysiere Simba Sleep"
→ Claude ruft python3 .claude/skills/competitor-ad-analysis/scripts/main.py --only "Simba Sleep"
  → schreibt automatisch in competitors + competitor_analyses
  → Board /competitors Page updated live

"Füg Mozart als Competitor hinzu, FB Page ID 123456"
→ Claude editiert competitors.json + läuft sync_to_board.py (oder direkt ein Supabase insert)
```

### Sync zwischen JSON und Supabase

`angles.json` und `competitors.json` bleiben die **Source of Truth für Skills**. Die Supabase-Tabellen sind eine **Display-Mirror für das Board**. Sync-Richtung ist einseitig:

```
JSON files  ──►  sync_to_board.py  ──►  Supabase  ──►  Board UI
```

Nach jedem manuellen Edit an `angles.json` oder `competitors.json`:
```bash
python3 scripts/sync_to_board.py            # beides synchen
python3 scripts/sync_to_board.py --only angles       # nur angles
python3 scripts/sync_to_board.py --only competitors  # nur competitors
```

`competitor-ad-analysis` schreibt zusätzlich automatisch `competitor_analyses` Rows nach jedem Run — das passiert im Skript selbst, kein separater Sync nötig.

## Competitors (aus Kick-Off)
- Simba Sleep (UK)
- Sleep Guys
- Mozart (Matratzen)
- Avocado (USA)
- NICHT Emma (zu konservativ)

## Workflow
1. Angle wählen (aus angles.json oder neu generieren)
2. Creative-Prompt bauen (JSON-Schema in creative-producer)
3. Generieren via Gemini → Compositor → Supabase Upload
4. Im Board reviewen, filtern, speichern

## Umgebung
- `.env` — Gemini API Key, Supabase Credentials, Brand ID
- Supabase Project: `cwwxtuuacxulrhvrilmu`
- Brand ID: `2a2349da-09c2-4e00-b739-0c652b7f62ea`
