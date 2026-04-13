#!/usr/bin/env python3
"""
brand-scrape.py — Scrape best-selling product images from a brand website.

Tries Shopify's products.json API first, falls back to HTML scraping.
Run from inside the brand-identity/ folder so outputs land in the right place.

Usage:
  cd ./brands/[brand-name]/brand-identity
  python3 ../../../skills/references/brand-scrape.py --scrape https://brand.com

Outputs:
  ./product-images/   — downloaded product images
  ./products.json     — product manifest (name, filename, product_url)
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List
from urllib.parse import urlparse

import requests


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

SCRAPE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str, max_len: int = 60) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:max_len]


def _get_image_ext(url: str) -> str:
    ext = Path(urlparse(url).path).suffix.lower()
    return ext if ext in IMAGE_EXTENSIONS else ".jpg"


def _download_image_file(url: str, dest: Path, headers: dict) -> bool:
    try:
        resp = requests.get(url, timeout=30, headers=headers)
        resp.raise_for_status()
        dest.write_bytes(resp.content)
        return True
    except Exception as e:
        print(f"    Download failed: {e}")
        return False


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

def _try_shopify_api(base_url: str, max_products: int) -> List[dict]:
    """Try Shopify's products.json API. Returns list of product dicts."""
    api_url = f"{base_url}/products.json?sort_by=best-selling&limit={max_products}"
    try:
        resp = requests.get(api_url, timeout=15, headers=SCRAPE_HEADERS)
        if not resp.ok:
            return []
        data = resp.json()
        products = []
        for p in data.get("products", [])[:max_products]:
            images = p.get("images", [])
            if not images:
                continue
            img_url = re.sub(r"\?.*$", "", images[0]["src"])
            products.append({
                "name": p["title"],
                "handle": p["handle"],
                "image_url": img_url,
                "product_url": f"{base_url}/products/{p['handle']}",
            })
        return products
    except Exception:
        return []


def _try_html_scrape(base_url: str, site_url: str, max_products: int) -> List[dict]:
    """Fallback HTML scraper using og:image and og:title tags."""
    candidate_pages = [
        f"{base_url}/collections/best-sellers",
        f"{base_url}/collections/bestsellers",
        f"{base_url}/best-sellers",
        f"{base_url}/bestsellers",
        f"{site_url}/collections/all?sort_by=best-selling",
        f"{base_url}/collections/all?sort_by=best-selling",
        f"{base_url}/shop",
        f"{base_url}/products",
        site_url,
    ]

    product_urls: list = []
    for page_url in candidate_pages:
        try:
            resp = requests.get(page_url, timeout=10, headers=SCRAPE_HEADERS)
            if not resp.ok:
                continue
            found = re.findall(
                r'href="(/(?:products|shop|store)/[^"?#\s]+)"',
                resp.text,
            )
            seen = set()
            for link in found:
                full = f"{base_url}{link}"
                if full not in seen:
                    seen.add(full)
                    product_urls.append(full)
            if product_urls:
                break
        except Exception:
            continue

    products = []
    for product_url in product_urls[:max_products * 2]:
        try:
            resp = requests.get(product_url, timeout=10, headers=SCRAPE_HEADERS)
            if not resp.ok:
                continue

            name_match = re.search(
                r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\'](.*?)["\']',
                resp.text, re.IGNORECASE
            ) or re.search(
                r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:title["\']',
                resp.text, re.IGNORECASE
            )
            name = name_match.group(1).strip() if name_match else product_url.rstrip("/").split("/")[-1]

            img_match = re.search(
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\'](.*?)["\']',
                resp.text, re.IGNORECASE
            ) or re.search(
                r'<meta[^>]+content=["\'](.*?)["\'][^>]+property=["\']og:image["\']',
                resp.text, re.IGNORECASE
            )
            if not img_match:
                continue

            img_url = img_match.group(1).strip()
            if img_url.startswith("//"):
                img_url = f"https:{img_url}"
            elif img_url.startswith("/"):
                img_url = f"{base_url}{img_url}"

            img_url = re.sub(r"\?.*$", "", img_url)

            products.append({
                "name": name,
                "handle": product_url.rstrip("/").split("/")[-1],
                "image_url": img_url,
                "product_url": product_url,
            })

            if len(products) >= max_products:
                break
        except Exception:
            continue

    return products


def scrape_product_images(site_url: str, max_products: int = 20) -> List[dict]:
    """
    Scrape best-selling products from a brand website and download their images.
    Run from inside brand-identity/ so outputs land in the right place.
    Saves images to ./product-images/ and writes ./products.json.
    """
    site_url = site_url.rstrip("/")
    parsed = urlparse(site_url)
    if not parsed.scheme:
        site_url = f"https://{site_url}"
        parsed = urlparse(site_url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    images_dir = Path("product-images")
    images_dir.mkdir(exist_ok=True)

    print(f"\nScraping best-selling products from {base_url}...\n")

    products_raw = _try_shopify_api(base_url, max_products)
    if products_raw:
        print(f"  Shopify API found {len(products_raw)} products.")
    else:
        print("  Shopify API not available — trying HTML scrape...")
        products_raw = _try_html_scrape(base_url, site_url, max_products)
        if products_raw:
            print(f"  HTML scrape found {len(products_raw)} products.")
        else:
            print("  Could not find products automatically.")
            print("  Tip: manually drop product images into ./product-images/ and create ./products.json")
            return []

    print(f"\nDownloading product images to ./product-images/...\n")

    manifest = []
    seen_slugs: dict = {}

    for p in products_raw[:max_products]:
        base_slug = _slugify(p["name"])

        if base_slug in seen_slugs:
            seen_slugs[base_slug] += 1
            slug = f"{base_slug}-{seen_slugs[base_slug]}"
        else:
            seen_slugs[base_slug] = 0
            slug = base_slug

        ext = _get_image_ext(p["image_url"])
        filename = f"{slug}{ext}"
        dest = images_dir / filename

        if dest.exists():
            print(f"  → {filename} (already exists, skipping)")
        else:
            print(f"  Downloading: {p['name']}...", end=" ", flush=True)
            ok = _download_image_file(p["image_url"], dest, SCRAPE_HEADERS)
            if not ok:
                continue
            print("✓")

        manifest.append({
            "name": p["name"],
            "filename": filename,
            "product_url": p["product_url"],
        })

    if not manifest:
        print("\n  Warning: no product images were saved.")
        return []

    manifest_path = Path("products.json")
    with open(manifest_path, "w") as f:
        json.dump({"products": manifest}, f, indent=2)

    print(f"\n  {len(manifest)} product(s) saved to ./product-images/")
    print(f"  Manifest → ./products.json\n")

    return manifest


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scrape best-selling product images from a brand website."
    )
    parser.add_argument(
        "--scrape", type=str, required=True, metavar="URL",
        help="Brand website URL to scrape (e.g. https://brand.com)"
    )
    parser.add_argument(
        "--max", type=int, default=20, metavar="N",
        help="Maximum number of products to download (default: 20)"
    )
    args = parser.parse_args()
    scrape_product_images(args.scrape, max_products=args.max)


if __name__ == "__main__":
    main()
