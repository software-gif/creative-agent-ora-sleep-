#!/usr/bin/env python3
"""Competitor Review Scraper — Scraped Trustpilot Reviews aller Competitors."""

import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime

try:
    import requests
except ImportError:
    print("Error: 'requests' not installed. Run: pip3 install requests")
    sys.exit(1)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", ".."))

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}

REVIEWS_PER_PAGE = 20


def fetch_page(trustpilot_url, page):
    """Fetch a single page of reviews from Trustpilot."""
    url = trustpilot_url.rstrip("/")
    if "de.trustpilot.com" not in url:
        url = url.replace("www.trustpilot.com", "de.trustpilot.com")

    page_url = f"{url}?page={page}"
    resp = requests.get(page_url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    html = resp.text
    match = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        return None, None, 0

    data = json.loads(match.group(1))
    pp = data.get("props", {}).get("pageProps", {})
    business = pp.get("businessUnit", {})
    reviews = pp.get("reviews", [])

    return business, reviews, len(reviews)


def extract_review(raw, competitor_name):
    """Extract relevant fields from a raw review."""
    consumer = raw.get("consumer", {})
    dates = raw.get("dates", {})

    return {
        "competitor": competitor_name,
        "rating": raw.get("rating"),
        "title": raw.get("headline", ""),
        "text": raw.get("text", ""),
        "author": consumer.get("displayName", ""),
        "date": dates.get("publishedDate", ""),
        "language": raw.get("language", ""),
        "is_verified": raw.get("isVerified", False),
    }


def scrape_competitor(name, trustpilot_url, max_pages, output_dir):
    """Scrape reviews for a single competitor."""
    print(f"\n{'='*50}")
    print(f"Scraping: {name}")
    print(f"URL: {trustpilot_url}")
    print(f"{'='*50}")

    comp_dir = os.path.join(output_dir, name.lower().replace(" ", "_"))
    os.makedirs(comp_dir, exist_ok=True)

    business, first_reviews, count = fetch_page(trustpilot_url, 1)
    if not business:
        print(f"  Error: Could not fetch {name}. Skipping.")
        return None

    total_on_platform = business.get("numberOfReviews", 0)
    total_pages = min(math.ceil(total_on_platform / REVIEWS_PER_PAGE), max_pages) if max_pages > 0 else math.ceil(total_on_platform / REVIEWS_PER_PAGE)

    print(f"  Total reviews: {total_on_platform}")
    print(f"  Pages to scrape: {total_pages}")

    all_reviews = [extract_review(r, name) for r in first_reviews]
    print(f"  Page 1: {len(first_reviews)} reviews")

    for page in range(2, total_pages + 1):
        time.sleep(2)
        _, reviews, count = fetch_page(trustpilot_url, page)
        if not reviews:
            print(f"  Page {page}: no data, stopping.")
            break
        all_reviews.extend([extract_review(r, name) for r in reviews])
        print(f"  Page {page}: {count} reviews (total: {len(all_reviews)})")

    # Save raw reviews
    raw_path = os.path.join(comp_dir, "reviews_raw.json")
    with open(raw_path, "w") as f:
        json.dump(all_reviews, f, indent=2, ensure_ascii=False)

    # Summary
    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in all_reviews:
        rating = r.get("rating", 0)
        if rating in dist:
            dist[rating] += 1

    negative = [r for r in all_reviews if r["rating"] <= 2]
    positive = [r for r in all_reviews if r["rating"] >= 4]

    # Extract top complaints from negative reviews
    complaints = [f"{r['title']}: {r['text'][:200]}" for r in negative if r.get("text")]

    summary = {
        "name": name,
        "trustpilot_url": trustpilot_url,
        "trust_score": business.get("trustScore"),
        "stars": business.get("stars"),
        "total_on_platform": total_on_platform,
        "scraped": len(all_reviews),
        "rating_distribution": dist,
        "negative_count": len(negative),
        "positive_count": len(positive),
        "top_complaints": complaints[:20],
    }

    sum_path = os.path.join(comp_dir, "summary.json")
    with open(sum_path, "w") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"  Rating: {summary['stars']} | Negative: {len(negative)} | Positive: {len(positive)}")
    print(f"  Saved to: {comp_dir}")

    return summary


def generate_market_overview(summaries, output_dir):
    """Generate aggregated market overview."""
    all_complaints = []
    for s in summaries:
        for c in s.get("top_complaints", []):
            all_complaints.append({"competitor": s["name"], "complaint": c})

    overview = {
        "scraped_at": datetime.now().isoformat()[:10],
        "competitors": [
            {
                "name": s["name"],
                "rating": s["stars"],
                "total_reviews": s["total_on_platform"],
                "scraped": s["scraped"],
                "negative_count": s["negative_count"],
                "positive_count": s["positive_count"],
            }
            for s in summaries
        ],
        "total_negative_reviews": sum(s["negative_count"] for s in summaries),
        "all_complaints": all_complaints,
    }

    overview_path = os.path.join(output_dir, "market_overview.json")
    with open(overview_path, "w") as f:
        json.dump(overview, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"MARKET OVERVIEW")
    print(f"{'='*50}")
    for s in summaries:
        print(f"  {s['name']}: {s['stars']}★ | {s['negative_count']} negative | {s['scraped']} scraped")
    print(f"\n  Total negative reviews: {overview['total_negative_reviews']}")
    print(f"  Saved: {overview_path}")

    return overview


def main():
    parser = argparse.ArgumentParser(description="Competitor Review Scraper")
    parser.add_argument("--competitor", default=None, help="Scrape single competitor by name")
    parser.add_argument("--max-pages", type=int, default=5, help="Max pages per competitor (default: 5)")
    parser.add_argument("--output-dir", default="reviews/competitors", help="Output directory")
    args = parser.parse_args()

    # Load competitors config
    config_path = os.path.join(PROJECT_ROOT, "competitors", "competitors.json")
    if not os.path.exists(config_path):
        print(f"Error: competitors.json not found at {config_path}")
        sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    competitors = config.get("competitors", [])

    # Filter if single competitor requested
    if args.competitor:
        competitors = [c for c in competitors if c["name"].lower() == args.competitor.lower()]
        if not competitors:
            print(f"Error: Competitor '{args.competitor}' not found in config.")
            sys.exit(1)

    # Filter only those with trustpilot_url
    scrapeable = [c for c in competitors if c.get("trustpilot_url")]
    skipped = [c for c in competitors if not c.get("trustpilot_url")]

    if skipped:
        print(f"Skipping {len(skipped)} competitors without Trustpilot URL:")
        for c in skipped:
            print(f"  - {c['name']}")

    if not scrapeable:
        print("Error: No competitors with Trustpilot URLs found.")
        sys.exit(1)

    print(f"\nScraping {len(scrapeable)} competitors (max {args.max_pages} pages each)...")

    output_dir = os.path.join(PROJECT_ROOT, args.output_dir)
    os.makedirs(output_dir, exist_ok=True)

    summaries = []
    for comp in scrapeable:
        summary = scrape_competitor(comp["name"], comp["trustpilot_url"], args.max_pages, output_dir)
        if summary:
            summaries.append(summary)
        time.sleep(3)  # Rate limit between competitors

    if summaries:
        generate_market_overview(summaries, output_dir)

    print(f"\nDone! {len(summaries)}/{len(scrapeable)} competitors scraped.")


if __name__ == "__main__":
    main()
