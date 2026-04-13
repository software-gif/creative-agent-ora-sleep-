#!/usr/bin/env python3
"""
competitor-ad-analysis — Systematic Meta Ad Library analysis across all competitors.

For each competitor in competitors.json with a facebook_page_id:
  1. Scrape ads via Apify (reusing ad-library-scraper functions)
  2. Download images locally
  3. Compute winner scores
Then aggregate across brands:
  4. Per-brand summary (count, format mix, active ratio, avg active days)
  5. Gemini 2.5 Flash Vision analyzes top-N winners per brand
  6. Gemini synthesizes strategic market insights for Ora Sleep
  7. Writes competitors/analysis/market_insights.json + market_report.md

Usage (run from creative-generator root):
  python3 .claude/skills/competitor-ad-analysis/scripts/main.py
  python3 .claude/skills/competitor-ad-analysis/scripts/main.py --only "Simba Sleep"
  python3 .claude/skills/competitor-ad-analysis/scripts/main.py --skip-scrape
  python3 .claude/skills/competitor-ad-analysis/scripts/main.py --top-n 10 --max-ads-per-brand 50

Env (loaded from .env at creative-generator root):
  APIFY_API_KEY — required for scraping
  GEMINI_API_KEY — required for analysis
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import requests


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]  # creative generator/
COMPETITORS_JSON = PROJECT_ROOT / "competitors" / "competitors.json"
BRANDING_DIR = PROJECT_ROOT / "branding"
ANGLES_JSON = PROJECT_ROOT / "angles" / "angles.json"
OUTPUT_DIR = PROJECT_ROOT / "competitors" / "analysis"
ENV_PATH = PROJECT_ROOT / ".env"

# Allow importing ad-library-scraper functions
AD_LIBRARY_SCRAPER_DIR = PROJECT_ROOT / ".claude" / "skills" / "ad-library-scraper" / "scripts"
sys.path.insert(0, str(AD_LIBRARY_SCRAPER_DIR))

try:
    from main import (  # type: ignore
        scrape_ads,
        download_static_images,
        calculate_winner_score,
    )
except ImportError as e:
    sys.exit(f"Could not import ad-library-scraper functions: {e}")


# ---------------------------------------------------------------------------
# Gemini config
# ---------------------------------------------------------------------------

TEXT_MODEL = "gemini-2.5-flash"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{TEXT_MODEL}:generateContent"


# ---------------------------------------------------------------------------
# Env loader
# ---------------------------------------------------------------------------

def load_env():
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            env[k.strip()] = v.strip().strip('"').strip("'")
    for k in ("APIFY_API_KEY", "GEMINI_API_KEY"):
        if k not in env and k in os.environ:
            env[k] = os.environ[k]
    missing = [k for k in ("APIFY_API_KEY", "GEMINI_API_KEY") if not env.get(k)]
    if missing:
        sys.exit(f"Error: missing env vars: {missing}")
    return env


# ---------------------------------------------------------------------------
# Gemini primitives
# ---------------------------------------------------------------------------

def _gemini_call(api_key, parts, temperature=0.4, max_tokens=4096):
    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "temperature": temperature,
            "topP": 0.9,
            "maxOutputTokens": max_tokens,
            "responseMimeType": "application/json",
        },
    }
    for attempt in range(3):
        try:
            r = requests.post(GEMINI_URL, params={"key": api_key}, json=payload, timeout=120)
            r.raise_for_status()
            data = r.json()
            candidates = data.get("candidates", [])
            if not candidates:
                time.sleep(2)
                continue
            text = "".join(
                p.get("text", "")
                for p in candidates[0].get("content", {}).get("parts", [])
            ).strip()
            if text:
                return text
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status == 429:
                wait = 8 * (attempt + 1)
                print(f"    rate limited, waiting {wait}s")
                time.sleep(wait)
                continue
            print(f"    HTTP {status}: {e}")
            time.sleep(2)
        except Exception as e:
            print(f"    Gemini error: {e}")
            time.sleep(2)
    raise RuntimeError("Gemini call failed after 3 attempts")


def _parse_json(raw):
    raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
    raw = re.sub(r"\s*```$", "", raw)
    return json.loads(raw)


# ---------------------------------------------------------------------------
# Per-ad vision analysis
# ---------------------------------------------------------------------------

VISION_SYSTEM = """You are a senior performance marketing analyst auditing competitor mattress ads for the Swiss/European market. For each image, extract:
- angle: one of [problem_pain, benefit, proof, curiosity, education, story, offer, trust]
- creative_style: one of [lifestyle, product_static, data_driven, testimonial, ugc, comparison, editorial, promo]
- copy_tone: one of [clinical, emotional, direct, urgent, playful, conversational, authoritative]
- offer_type: null or one of [percent_discount, price_mention, free_shipping, trial_nights, bundle, guarantee, financing]
- hook_summary: one sentence in English summarizing what the ad is trying to sell and how
- health_claim_risk: true if the ad makes medical/therapeutic claims that could trigger Meta policy issues, false otherwise

Return a JSON object matching this schema exactly. Be concrete and consistent — use the enums."""


def analyze_ad_images(api_key, ads_with_paths, top_n):
    """For top N winners per brand, run Gemini Vision per ad image.

    Returns list of {ad_id, headline, body, score, analysis}
    """
    results = []
    for ad, score, local_paths in ads_with_paths[:top_n]:
        if not local_paths:
            continue
        img_path = Path(local_paths[0])
        try:
            img_bytes = img_path.read_bytes()
        except Exception as e:
            print(f"    skip {ad.get('ad_archive_id')}: {e}")
            continue

        mime = "image/jpeg" if img_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
        snapshot = ad.get("snapshot", {})
        body = (snapshot.get("body") or {}).get("text", "") or ""
        title = snapshot.get("title", "") or ""
        cta = snapshot.get("cta_text", "") or ""

        user_prompt = f"""Analyze this competitor ad image. Metadata:
- Title/headline text: {title[:200]}
- Body/primary text: {body[:400]}
- CTA: {cta}

Return the JSON schema described in the system instructions."""

        parts = [
            {"text": VISION_SYSTEM},
            {"text": user_prompt},
            {"inline_data": {"mime_type": mime, "data": base64.b64encode(img_bytes).decode("utf-8")}},
        ]

        try:
            raw = _gemini_call(api_key, parts, temperature=0.3, max_tokens=1024)
            analysis = _parse_json(raw)
        except Exception as e:
            print(f"    vision failed for {ad.get('ad_archive_id')}: {e}")
            continue

        results.append({
            "ad_id": ad.get("ad_archive_id"),
            "headline": title[:150],
            "body": body[:400],
            "cta": cta,
            "is_active": ad.get("is_active", False),
            "start_date": ad.get("start_date_formatted", ""),
            "winner_score": score,
            "image_path": str(img_path.relative_to(PROJECT_ROOT)) if img_path.is_relative_to(PROJECT_ROOT) else str(img_path),
            "analysis": analysis,
        })
    return results


# ---------------------------------------------------------------------------
# Per-brand summary
# ---------------------------------------------------------------------------

def summarize_brand(name, ads):
    """Compute per-brand stats from raw ads list."""
    total = len(ads)
    active = sum(1 for a in ads if a.get("is_active"))

    fmt_counter = Counter()
    active_days_list = []
    for ad in ads:
        snapshot = ad.get("snapshot", {})
        fmt_counter[snapshot.get("display_format", "UNKNOWN")] += 1
        start_str = ad.get("start_date_formatted", "")
        if start_str:
            try:
                start = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                active_days_list.append((datetime.now() - start).days)
            except ValueError:
                pass

    avg_days = round(sum(active_days_list) / len(active_days_list)) if active_days_list else 0

    return {
        "brand": name,
        "total_ads": total,
        "active_ads": active,
        "inactive_ads": total - active,
        "active_ratio": round(active / total, 2) if total else 0,
        "format_distribution": dict(fmt_counter),
        "avg_active_days": avg_days,
    }


# ---------------------------------------------------------------------------
# Per-brand orchestration
# ---------------------------------------------------------------------------

def process_competitor(env, competitor, args):
    name = competitor["name"]
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    page_id = competitor.get("facebook_page_id")

    brand_dir = PROJECT_ROOT / "competitors" / slug
    brand_dir.mkdir(parents=True, exist_ok=True)
    raw_path = brand_dir / "ads_raw.json"
    analyzed_path = brand_dir / "ads_analyzed.json"

    if not page_id:
        print(f"\n[skip] {name}: no facebook_page_id in competitors.json")
        return {"brand": name, "slug": slug, "status": "skipped_no_page_id"}

    # 1. Scrape (or use cache)
    if args.skip_scrape and raw_path.exists():
        print(f"\n[cache] {name}: using {raw_path.relative_to(PROJECT_ROOT)}")
        ads = json.loads(raw_path.read_text())
    else:
        print(f"\n[scrape] {name} (page_id={page_id})")
        try:
            ads = scrape_ads(env["APIFY_API_KEY"], page_id, max_ads=args.max_ads_per_brand)
        except Exception as e:
            print(f"  ✗ scrape failed: {e}")
            return {"brand": name, "slug": slug, "status": "scrape_failed", "error": str(e)}
        raw_path.write_text(json.dumps(ads, indent=2, ensure_ascii=False))

    if not ads:
        print(f"  no ads found")
        return {"brand": name, "slug": slug, "status": "no_ads"}

    # 2. Download images
    local_paths = download_static_images(ads, str(brand_dir))

    # 3. Score + rank
    scored = []
    for ad in ads:
        score = calculate_winner_score(ad)
        ad_paths = local_paths.get(ad.get("ad_archive_id"), [])
        scored.append((ad, score, ad_paths))
    scored.sort(key=lambda x: x[1], reverse=True)

    analyzed_path.write_text(json.dumps(
        [{"ad_archive_id": a.get("ad_archive_id"), "winner_score": s, "is_active": a.get("is_active")}
         for a, s, _ in scored],
        indent=2,
        ensure_ascii=False,
    ))

    # 4. Vision analysis on top-N
    print(f"  analyzing top {min(args.top_n, len(scored))} winners via Gemini Vision...")
    vision_results = analyze_ad_images(env["GEMINI_API_KEY"], scored, args.top_n)

    # 5. Per-brand summary + save winners
    summary = summarize_brand(name, ads)
    winners_path = OUTPUT_DIR / "ads_by_brand" / f"{slug}_winners.json"
    winners_path.parent.mkdir(parents=True, exist_ok=True)
    winners_path.write_text(json.dumps({
        "brand": name,
        "summary": summary,
        "winners": vision_results,
    }, indent=2, ensure_ascii=False))

    print(f"  ✓ {summary['total_ads']} ads | {summary['active_ads']} active | formats: {summary['format_distribution']}")

    return {
        "brand": name,
        "slug": slug,
        "status": "ok",
        "summary": summary,
        "vision_results": vision_results,
    }


# ---------------------------------------------------------------------------
# Strategic synthesis
# ---------------------------------------------------------------------------

SYNTHESIS_SYSTEM = """You are the lead performance strategist for Ora Sleep, a Swiss D2C mattress brand. You have just been handed a structured audit of competitor ads in the Swiss/European mattress market.

Your job: synthesize this into a strategic market report that the Ora creative team will use to decide where to invest next. Be concrete, opinionated, and specific. No fluff. No generic advice.

Focus on:
1. OVERSATURATED ANGLES — which angles are ALL competitors pushing? (Ora should avoid direct clones of these.)
2. UNDEREXPLOITED ANGLES — what's missing across the board that Ora could own?
3. FORMAT INSIGHTS — who uses what format? What's the gap?
4. COPY THEMES — recurring hooks, pricing tactics, CTA patterns.
5. HEALTH CLAIM RISK PATTERNS — which competitors make medical/therapeutic claims Ora must explicitly avoid?
6. ORA DIFFERENTIATION — 3 to 5 concrete, actionable recommendations for the next creative sprint. Each recommendation should be specific enough to brief a designer directly.

Ora brand context:
- Swiss Made, Testsieger 2026, direct-to-consumer
- Hero product: Ora Ultra Matratze (CHF 899-1699), Ora Ultra Topper (CHF 799-899)
- HARD GUARDRAIL: Ora cannot make health claims (no "heilt", "garantiert", "klinisch getestet"). All outcomes must be phrased as "customer-reported".
- Kick-off philosophy: MAXIMAL CREATIVE DIVERSITY (Andromeda) — performance > brand consistency.
- Top-performing Ora ad historically: the "93 Prozent" simple high-contrast statement ad.

Return a JSON object matching this schema EXACTLY:
{
  "oversaturated_angles": [
    {"angle": "<angle name>", "brands": ["<brand>"], "evidence": "<specific ads/hooks observed>", "ora_implication": "<what Ora should NOT do>"}
  ],
  "underexploited_angles": [
    {"angle": "<angle name>", "opportunity": "<why no one is doing this>", "ora_move": "<concrete creative direction>"}
  ],
  "format_insights": {
    "dominant_format": "<IMAGE|VIDEO|DCO|CAROUSEL>",
    "by_brand": {"<brand>": {"<format>": <count>}},
    "gap": "<which format/angle combination is empty>"
  },
  "copy_themes": {
    "recurring_hooks": ["<hook>"],
    "pricing_tactics": ["<tactic>"],
    "ctas_observed": ["<cta>"],
    "tone_patterns": "<observation>"
  },
  "health_claim_risks_observed": [
    {"brand": "<brand>", "claim": "<exact phrasing>", "ora_must_avoid": "<how Ora should phrase it instead>"}
  ],
  "ora_differentiation": [
    {"recommendation": "<headline for the recommendation>", "rationale": "<why>", "concrete_action": "<what the designer should produce>", "priority": "high|medium|low"}
  ]
}"""


def synthesize_market_insights(api_key, brand_results, ora_context):
    # Build a concise payload for the strategist
    digest = {
        "ora_context": ora_context,
        "competitors": [],
    }
    for r in brand_results:
        if r["status"] != "ok":
            digest["competitors"].append({
                "brand": r["brand"],
                "status": r["status"],
            })
            continue
        digest["competitors"].append({
            "brand": r["brand"],
            "summary": r["summary"],
            "top_winners": [
                {
                    "headline": w.get("headline"),
                    "body_snippet": (w.get("body") or "")[:200],
                    "cta": w.get("cta"),
                    "is_active": w.get("is_active"),
                    "start_date": w.get("start_date"),
                    "winner_score": w.get("winner_score"),
                    "analysis": w.get("analysis"),
                }
                for w in (r.get("vision_results") or [])
            ],
        })

    user_prompt = (
        "Here is the structured competitor audit data. "
        "Synthesize it into the strategic market report JSON defined in your system instructions.\n\n"
        + json.dumps(digest, ensure_ascii=False, indent=2)
    )

    parts = [
        {"text": SYNTHESIS_SYSTEM},
        {"text": user_prompt},
    ]
    raw = _gemini_call(api_key, parts, temperature=0.5, max_tokens=8192)
    return _parse_json(raw)


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------

def render_markdown_report(insights, brand_results, run_meta):
    lines = []
    lines.append(f"# Competitor Ad Analysis — Ora Sleep Market Report")
    lines.append("")
    lines.append(f"_Generated: {run_meta['generated_at']} · Brands analyzed: {run_meta['brands_ok']}/{run_meta['brands_total']} · Ads scraped: {run_meta['total_ads']}_")
    lines.append("")

    # Executive summary
    lines.append("## Executive Summary")
    lines.append("")
    for r in brand_results:
        if r["status"] != "ok":
            lines.append(f"- **{r['brand']}** — {r['status']}")
            continue
        s = r["summary"]
        fmts = ", ".join(f"{k}: {v}" for k, v in s["format_distribution"].items())
        lines.append(
            f"- **{s['brand']}** — {s['total_ads']} ads · "
            f"{s['active_ads']} active ({int(s['active_ratio']*100)}%) · "
            f"avg runtime {s['avg_active_days']}d · formats: {fmts}"
        )
    lines.append("")

    # Oversaturated
    lines.append("## Oversaturated Angles")
    lines.append("_All competitors are pushing these. Avoid direct clones._")
    lines.append("")
    for a in insights.get("oversaturated_angles", []):
        lines.append(f"### {a.get('angle')}")
        lines.append(f"- **Brands:** {', '.join(a.get('brands', []))}")
        lines.append(f"- **Evidence:** {a.get('evidence', '')}")
        lines.append(f"- **Ora implication:** {a.get('ora_implication', '')}")
        lines.append("")

    # Gaps
    lines.append("## Underexploited Angles (Whitespace)")
    lines.append("_Nobody else is doing this. Opportunity for Ora._")
    lines.append("")
    for a in insights.get("underexploited_angles", []):
        lines.append(f"### {a.get('angle')}")
        lines.append(f"- **Why open:** {a.get('opportunity', '')}")
        lines.append(f"- **Ora move:** {a.get('ora_move', '')}")
        lines.append("")

    # Formats
    fi = insights.get("format_insights", {})
    lines.append("## Format Insights")
    lines.append(f"- **Dominant format:** {fi.get('dominant_format', '—')}")
    lines.append(f"- **Gap:** {fi.get('gap', '—')}")
    if fi.get("by_brand"):
        lines.append("- **By brand:**")
        for b, fmts in fi["by_brand"].items():
            lines.append(f"  - {b}: {fmts}")
    lines.append("")

    # Copy themes
    ct = insights.get("copy_themes", {})
    lines.append("## Copy Themes")
    if ct.get("recurring_hooks"):
        lines.append(f"- **Recurring hooks:** {', '.join(ct['recurring_hooks'])}")
    if ct.get("pricing_tactics"):
        lines.append(f"- **Pricing tactics:** {', '.join(ct['pricing_tactics'])}")
    if ct.get("ctas_observed"):
        lines.append(f"- **CTAs observed:** {', '.join(ct['ctas_observed'])}")
    if ct.get("tone_patterns"):
        lines.append(f"- **Tone patterns:** {ct['tone_patterns']}")
    lines.append("")

    # Health claims
    risks = insights.get("health_claim_risks_observed", [])
    if risks:
        lines.append("## Health Claim Risks Observed")
        lines.append("_What competitors say that Ora **must not** say._")
        lines.append("")
        for r in risks:
            lines.append(f"- **{r.get('brand')}** — claim: _{r.get('claim')}_")
            lines.append(f"  - Ora alternative: {r.get('ora_must_avoid')}")
        lines.append("")

    # Recommendations
    lines.append("## Ora Differentiation Recommendations")
    lines.append("")
    for rec in insights.get("ora_differentiation", []):
        priority = rec.get("priority", "medium").upper()
        lines.append(f"### [{priority}] {rec.get('recommendation', '')}")
        lines.append(f"- **Why:** {rec.get('rationale', '')}")
        lines.append(f"- **Concrete action:** {rec.get('concrete_action', '')}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def load_ora_context():
    ctx = {}
    brand_path = BRANDING_DIR / "brand.json"
    guidelines_path = BRANDING_DIR / "brand_guidelines.json"
    angles_path = ANGLES_JSON

    if brand_path.exists():
        brand = json.loads(brand_path.read_text())
        ctx["products"] = brand.get("products", [])
        ctx["trust_signals"] = brand.get("trust_signals", [])
    if guidelines_path.exists():
        g = json.loads(guidelines_path.read_text())
        ctx["tone_of_voice"] = g.get("tone_of_voice", {})
    if angles_path.exists():
        a = json.loads(angles_path.read_text())
        angles = a if isinstance(a, list) else a.get("angles", [])
        ctx["current_angles"] = [x.get("name") or x.get("key") for x in angles]
    return ctx


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-ads-per-brand", type=int, default=30)
    parser.add_argument("--only", type=str, default=None, help="Run only this competitor by name")
    parser.add_argument("--skip-scrape", action="store_true", help="Use cached ads_raw.json, skip Apify")
    parser.add_argument("--top-n", type=int, default=5, help="Top N winners to analyze via Gemini Vision per brand")
    args = parser.parse_args()

    env = load_env()

    if not COMPETITORS_JSON.exists():
        sys.exit(f"Error: {COMPETITORS_JSON} not found")
    competitors_data = json.loads(COMPETITORS_JSON.read_text())
    competitors = competitors_data.get("competitors", [])

    if args.only:
        competitors = [c for c in competitors if c["name"].lower() == args.only.lower()]
        if not competitors:
            sys.exit(f"Error: competitor '{args.only}' not found in competitors.json")

    print(f"=== Competitor Ad Analysis ===")
    print(f"Competitors to process: {len(competitors)}")
    if args.skip_scrape:
        print(f"Mode: skip-scrape (using cached data)")
    print()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    brand_results = []
    for c in competitors:
        try:
            result = process_competitor(env, c, args)
            brand_results.append(result)
        except KeyboardInterrupt:
            print("\nInterrupted. Writing partial results...")
            break
        except Exception as e:
            print(f"  ✗ {c['name']} failed: {e}")
            brand_results.append({"brand": c["name"], "status": "exception", "error": str(e)})

    # Synthesis
    ok_results = [r for r in brand_results if r.get("status") == "ok"]
    if not ok_results:
        print("\nNo competitors processed successfully. Nothing to synthesize.")
        print("Tip: fill in facebook_page_id for each competitor in competitors.json.")
        print("How to find Page IDs: see SKILL.md")
        sys.exit(1)

    print(f"\n=== Synthesizing market insights ({len(ok_results)} brands) ===")
    ora_context = load_ora_context()
    insights = synthesize_market_insights(env["GEMINI_API_KEY"], brand_results, ora_context)

    # Persist outputs
    total_ads = sum(r["summary"]["total_ads"] for r in ok_results)
    run_meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brands_total": len(brand_results),
        "brands_ok": len(ok_results),
        "total_ads": total_ads,
        "max_ads_per_brand": args.max_ads_per_brand,
        "top_n_vision": args.top_n,
    }

    insights_payload = {
        "meta": run_meta,
        "insights": insights,
    }
    (OUTPUT_DIR / "market_insights.json").write_text(
        json.dumps(insights_payload, indent=2, ensure_ascii=False)
    )

    report = render_markdown_report(insights, brand_results, run_meta)
    (OUTPUT_DIR / "market_report.md").write_text(report)

    print()
    print(f"✓ market_insights.json → {(OUTPUT_DIR / 'market_insights.json').relative_to(PROJECT_ROOT)}")
    print(f"✓ market_report.md     → {(OUTPUT_DIR / 'market_report.md').relative_to(PROJECT_ROOT)}")
    print()

    # Quick CLI summary
    recs = insights.get("ora_differentiation", [])
    if recs:
        print(f"Top {min(3, len(recs))} recommendations for Ora:")
        for r in recs[:3]:
            print(f"  [{r.get('priority', '?').upper()}] {r.get('recommendation', '')}")


if __name__ == "__main__":
    main()
