# Briefing Agent

> Generiert Meta-optimierte Ad Copy + Creative Briefing für ein bestehendes Creative. Gemini 2.5 Flash liest das Bild + Brand Voice + Angle-Daten und schreibt alle Copy-Felder zurück nach Supabase.

## Zweck

Zwischen "Creative generiert" und "Ad bei Meta uploaden" fehlt ein Schritt: **die Ad-Copy schreiben**. Manuell ist das zeitaufwändig und inkonsistent. Der Briefing Agent macht das automatisch — eingeschränkt durch die Ora Sleep Brand Voice und die Health-Claims-Guardrail.

## Input

Eine Creative-ID aus Supabase. Das Skript liest selbst:
- Die `creatives`-Row (angle, sub_angle, format, hook_text, storage_path)
- Das Bild aus Supabase Storage (für Vision-Analyse)
- `branding/brand_guidelines.json` (Tone of Voice)
- `branding/brand.json` (Produktdaten, Trust Signals)
- `angles/angles.json` (Angle-Kontext + Sub-Angles)

## Output

Schreibt zurück in dieselbe `creatives`-Row:
- `primary_text` — Meta Caption (~125 Zeichen optimal, max 500)
- `headlines` — Array mit 5 Varianten à max 40 Zeichen (Meta Feed Limit)
- `description` — 30 Zeichen Meta Link Description
- `cta` — Meta Standard-CTA (z.B. "Jetzt kaufen", "Mehr erfahren")
- `briefing_rationale` — 2-3 Sätze: Warum dieses Creative, Angle-Rationale
- `target_audience` — Kurzer Descriptor (z.B. "30-55, chronische Rückenschmerzen, DACH")
- `copy_generated_at` — Timestamp

## Health Claims Guardrail

**HARTE REGEL — im Prompt eingebaut:**

❌ "heilt Rückenschmerzen" / "garantiert besseren Schlaf" / "beseitigt Schlafstörungen" / "klinisch getestet" / "medizinisch bewiesen" / "therapeutisch"

✅ "49% unserer Kunden berichten von weniger Schmerzen" / "laut Kundenumfrage" / "viele Kunden berichten" / "bei vielen Schlafenden"

Verstoß führt zu Meta Ad-Account-Sperre. Das ist die größte Sorge des Kunden.

## Aufruf

```bash
cd "ora-sleep/creative generator"
python3 .claude/skills/briefing-agent/scripts/main.py <creative_id>
```

Mehrere Creatives auf einmal:
```bash
python3 .claude/skills/briefing-agent/scripts/main.py <id1> <id2> <id3>
```

## Trigger

1. **Automatisch nach dem Upload** — `ai-visuals/scripts/upload_to_board.py` ruft das Skript für jede neu eingefügte Creative-Row auf.
2. **Manuell nach dem Generieren** — Claude Code nutzt es auf Befehl, z.B. "run briefing-agent on creative fc33...".
3. **Regenerate-Button im Board** — Next.js API-Route spawnt das Skript, UI zeigt Ergebnis direkt.

## Kosten

Gemini 2.5 Flash mit Vision ist extrem günstig: ~0.00015 USD pro Creative. Bei 1000 Creatives im Monat ~0.15 USD. Claude 3.5 Sonnet wäre ~0.02 USD × 1000 = 20 USD, also ~130× teurer.

## Scripts

- `scripts/main.py` — Das Herzstück. Gemini-Call, Supabase Read/Write, Guardrail-Prompt.
