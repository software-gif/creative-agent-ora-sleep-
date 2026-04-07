#!/usr/bin/env python3
"""Angle Generator — Prepares review + survey + winner data for Claude to generate Ad Angles."""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))


def load_brand():
    """Load brand.json."""
    brand_path = os.path.join(PROJECT_ROOT, "branding", "brand.json")
    if not os.path.exists(brand_path):
        print("Error: brand.json not found.")
        sys.exit(1)
    with open(brand_path) as f:
        return json.load(f)


def load_trustpilot_reviews():
    """Load Trustpilot reviews."""
    raw_path = os.path.join(PROJECT_ROOT, "reviews", "trustpilot", "reviews_raw.json")
    if not os.path.exists(raw_path):
        print("Warning: reviews/trustpilot/reviews_raw.json not found. Skipping Trustpilot data.")
        return []
    with open(raw_path) as f:
        return json.load(f)


def load_judgeme_feedback():
    """Load Judge.me customer feedback survey."""
    raw_path = os.path.join(PROJECT_ROOT, "reviews", "judgeme", "feedback_raw.json")
    if not os.path.exists(raw_path):
        print("Warning: reviews/judgeme/feedback_raw.json not found. Skipping Judge.me data.")
        return None
    with open(raw_path) as f:
        return json.load(f)


def load_winners():
    """Load winner ad analysis."""
    path = os.path.join(PROJECT_ROOT, "winners", "ads_analyzed.json")
    if not os.path.exists(path):
        print("Warning: winners/ads_analyzed.json not found. Proceeding without winner data.")
        return []
    with open(path) as f:
        return json.load(f)


def prepare_summary(brand, trustpilot_reviews, judgeme_data, winners):
    """Prepare a structured summary for Claude to analyze."""
    # Trustpilot reviews
    negative = [r for r in trustpilot_reviews if r.get("rating", 0) <= 2]
    positive = [r for r in trustpilot_reviews if r.get("rating", 0) >= 4]
    neutral = [r for r in trustpilot_reviews if r.get("rating", 0) == 3]

    negative.sort(key=lambda r: r.get("rating", 0))
    positive.sort(key=lambda r: -r.get("rating", 0))

    def format_reviews(review_list, max_count=40):
        formatted = []
        for r in review_list[:max_count]:
            text = r.get("text", "").strip()
            title = r.get("title", "").strip()
            if text or title:
                entry = f"[{r.get('rating', '?')}★]"
                if title:
                    entry += f" {title}:"
                entry += f" {text[:400]}"
                formatted.append(entry)
        return "\n".join(formatted)

    # Winner ads summary
    static_winners = [w for w in winners if w.get("display_format") in ("IMAGE", "DCO")]
    static_winners.sort(key=lambda w: -w.get("winner_score", 0))
    winner_lines = []
    for w in static_winners[:15]:
        body = w.get("body_text", "")[:250]
        title = w.get("title", "")[:100]
        score = w.get("winner_score", 0)
        winner_lines.append(f"[Score: {score}] {title} — {body}")

    # Judge.me survey summary
    judgeme_summary = {}
    if judgeme_data:
        judgeme_summary = judgeme_data.get("summary", {})
        # Extract top comments from promoters
        top_comments = []
        for r in judgeme_data.get("responses", []):
            if r.get("kommentar") and r.get("nps_score", 0) >= 9:
                top_comments.append(f"[NPS {r['nps_score']}] {r['kommentar']}")
        judgeme_summary["top_promoter_comments"] = top_comments[:15]

    summary = {
        "brand": {
            "name": brand.get("name", ""),
            "category": brand.get("category", ""),
            "shop_url": brand.get("shop_url", ""),
            "target_market": brand.get("target_market", ""),
        },
        "trustpilot": {
            "total": len(trustpilot_reviews),
            "negative": len(negative),
            "neutral": len(neutral),
            "positive": len(positive),
            "negative_reviews": format_reviews(negative),
            "positive_reviews": format_reviews(positive),
            "neutral_reviews": format_reviews(neutral),
        },
        "judgeme_survey": judgeme_summary,
        "winner_ads": "\n".join(winner_lines),
    }

    return summary


def main():
    parser = argparse.ArgumentParser(description="Angle Generator — Data Preparation")
    parser.add_argument("--output-dir", default="angles", help="Output directory")
    args = parser.parse_args()

    output_dir = os.path.join(PROJECT_ROOT, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    # Load all data
    print("Loading brand data...")
    brand = load_brand()
    print(f"  Brand: {brand.get('name', '')}")

    print("Loading Trustpilot reviews...")
    trustpilot = load_trustpilot_reviews()
    print(f"  {len(trustpilot)} Trustpilot reviews loaded")

    print("Loading Judge.me feedback...")
    judgeme = load_judgeme_feedback()
    if judgeme:
        print(f"  {judgeme.get('total_responses', 0)} Judge.me survey responses loaded")
    else:
        print("  No Judge.me data found")

    print("Loading winner ads...")
    winners = load_winners()
    print(f"  {len(winners)} winner ads loaded")

    # Prepare summary
    summary = prepare_summary(brand, trustpilot, judgeme, winners)

    # Save summary
    summary_path = os.path.join(output_dir, "review_summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    print(f"\nSaved review summary: {summary_path}")

    # Print for Claude
    tp = summary["trustpilot"]
    print(f"\n{'='*60}")
    print(f"BRAND: {summary['brand']['name']} ({summary['brand']['category']})")
    print(f"TRUSTPILOT: {tp['total']} reviews ({tp['negative']} neg, {tp['neutral']} neutral, {tp['positive']} pos)")
    if judgeme:
        js = summary["judgeme_survey"]
        print(f"JUDGE.ME SURVEY: {judgeme.get('total_responses', 0)} responses, NPS {js.get('nps_avg', '?')}")
    print(f"WINNER ADS: {len(winners)} static ads analyzed")
    print(f"{'='*60}")

    print(f"\n--- TRUSTPILOT: NEGATIVE ({tp['negative']}) ---")
    print(tp["negative_reviews"][:3000])

    print(f"\n--- TRUSTPILOT: POSITIVE ({tp['positive']}) ---")
    print(tp["positive_reviews"][:3000])

    if judgeme and "top_promoter_comments" in summary.get("judgeme_survey", {}):
        print(f"\n--- JUDGE.ME: TOP PROMOTER COMMENTS ---")
        for c in summary["judgeme_survey"]["top_promoter_comments"]:
            print(f"  {c}")

    print(f"\n--- TOP WINNER ADS ---")
    print(summary["winner_ads"][:2000])

    print(f"\n{'='*60}")
    print("Data preparation complete.")
    print(f"Claude should now analyze this data and update: {output_dir}/angles.json")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
