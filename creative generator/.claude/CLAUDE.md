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
1. **angle-generator** — Angles aus Reviews/Daten ableiten
2. **creative-producer** — Gemini-basierte Ad-Generierung + Compositor + Supabase Upload
3. **sales-event-producer** — Sales-Event-Creatives (Black Friday etc.)
4. **competitor-cloner** — Competitor-Ads als Inspiration klonen
5. **product-scraper** — Shopify-Produktdaten scrapen
6. **review-scraper** — Trustpilot Reviews scrapen
7. **ad-library-scraper** — Meta Ad Library scrapen (via Apify)

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
