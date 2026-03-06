"""
Real-time scraper for Nagpur real estate data.

Scrapes MagicBricks → cleans data → inserts into the SQLite database.
Can be called from the backend API, scheduler, or run directly.
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import re
import time
import random
import logging
from datetime import datetime, date

from database import get_session, RawListing, LocalitySnapshot, ScrapeLog

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

CITY = "Nagpur"

# ── HTTP helpers ─────────────────────────────────────────────────────────────

def _get_headers(referer=None):
    headers = {
        "authority": "www.magicbricks.com",
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "accept-language": "en-US,en;q=0.9",
        "cache-control": "no-cache",
        "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "same-origin",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/120.0.0.0 Safari/537.36",
    }
    if referer:
        headers["referer"] = referer
    return headers


def _clean_numeric(text: str) -> float:
    """Extract a numeric value from a price/area string."""
    if not text or "N/A" in text or "Call for Price" in text:
        return 0.0

    text = text.lower().replace(",", "").strip()

    multiplier = 1
    if "lac" in text or "lakh" in text:
        multiplier = 100_000
    elif "cr" in text or "crore" in text:
        multiplier = 10_000_000

    match = re.search(r"(\d+\.?\d*)", text)
    if match:
        return float(match.group(1)) * multiplier
    return 0.0


# ── Cleaning helpers (from nagpur_real_estate_cleaned.py) ─────────────────

def _clean_locality_name(locality: str) -> str:
    """Normalize a locality name (uppercase, remove noise words, etc.)."""
    if not locality or pd.isna(locality):
        return ""

    locality = str(locality).upper()

    unwanted = ["AREA", "NAGPUR", "CITY", "DISTRICT", "MAHARASHTRA",
                 "ROAD", "PHASE", "NEAR", "OPP", "OPPOSITE"]
    for word in unwanted:
        locality = locality.replace(word, "")

    locality = re.sub(r"\d+", "", locality)            # remove numbers
    locality = re.sub(r"[^A-Z\s]", "", locality)       # keep only letters & spaces
    locality = re.sub(r"\s+", " ", locality).strip()    # collapse whitespace
    return locality


# ── Core scraping logic ──────────────────────────────────────────────────────

def scrape_magicbricks(target_count: int = 300) -> list[dict]:
    """
    Scrape property listings from MagicBricks for Nagpur.
    Returns a list of dicts (raw listing rows).
    """
    all_data: list[dict] = []
    scrape_date = date.today()
    session = requests.Session()

    # warm up the session (get cookies)
    try:
        session.get("https://www.magicbricks.com/", headers=_get_headers(), timeout=15)
        time.sleep(random.uniform(2, 4))
    except Exception:
        logger.warning("Session warm-up failed, continuing anyway…")

    logger.info("Starting MagicBricks scrape for %s (target: %d)", CITY, target_count)

    page = 1
    while len(all_data) < target_count:
        url = (
            f"https://www.magicbricks.com/property-for-sale/residential-real-estate?"
            f"&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,"
            f"Studio-Apartment,Residential-House,Villas,Residential-Plot"
            f"&cityName={CITY}&page={page}"
        )
        referer = (
            "https://www.magicbricks.com/"
            if page == 1
            else f"https://www.magicbricks.com/property-for-sale/residential-real-estate?&cityName={CITY}&page={page - 1}"
        )

        try:
            resp = session.get(url, headers=_get_headers(referer), timeout=25)
            if resp.status_code == 403:
                logger.warning("IP blocked (403) at page %d — stopping.", page)
                break

            soup = BeautifulSoup(resp.content, "html.parser")
            cards = soup.find_all("div", class_="mb-srp__card")

            if not cards:
                logger.info("No listings found on page %d — ending.", page)
                break

            for card in cards:
                try:
                    # Listing URL
                    link_tag = (
                        card.find("a", class_="mb-srp__card__link")
                        or card.find("a", class_="mb-srp__card--title")
                        or card.find("a", href=True)
                    )
                    listing_url = ""
                    if link_tag and "href" in link_tag.attrs:
                        listing_url = link_tag["href"]
                        if not listing_url.startswith("http"):
                            listing_url = "https://www.magicbricks.com" + listing_url

                    # Locality
                    loc_tag = (
                        card.find("span", class_="mb-srp__card--location")
                        or card.find("div", class_="mb-srp__card__location")
                    )
                    full_location = loc_tag.text.strip() if loc_tag else ""
                    if not full_location:
                        title_tag = card.find(["h2", "span"], class_="mb-srp__card--title")
                        if title_tag and " in " in title_tag.text:
                            full_location = title_tag.text.split(" in ")[-1]
                    locality = full_location.split(",")[0].strip().upper() if full_location else "UNKNOWN"
                    if locality == "NAGPUR" or not locality:
                        locality = "UNKNOWN"

                    # Property type
                    title_tag = card.find(["h2", "span"], class_="mb-srp__card--title")
                    title_text = title_tag.text.strip().lower() if title_tag else ""
                    property_type = "Flat"
                    if "plot" in title_text:
                        property_type = "Plot"
                    elif "house" in title_text:
                        property_type = "House"
                    elif "villa" in title_text:
                        property_type = "Villa"
                    elif "penthouse" in title_text:
                        property_type = "Penthouse"

                    # Price
                    price_raw = card.find("div", class_="mb-srp__card__price--amount")
                    total_price = _clean_numeric(price_raw.text) if price_raw else 0

                    # Area
                    area_tag = (
                        card.find("div", {"data-summary": "displayUnit"})
                        or card.find("div", class_="mb-srp__card__summary--value")
                        or card.find("div", class_="mb-srp__card__area")
                    )
                    area_sqft = _clean_numeric(area_tag.text) if area_tag else 0

                    # Price per sqft
                    pps_tag = (
                        card.find("div", class_="mb-srp__card__price--size")
                        or card.find("div", class_="mb-srp__card__pps")
                    )
                    price_per_sqft = _clean_numeric(pps_tag.text) if pps_tag else 0

                    # Compute price_per_sqft if missing but other fields exist
                    if price_per_sqft == 0 and total_price > 0 and area_sqft > 0:
                        price_per_sqft = round(total_price / area_sqft, 2)

                    if locality != "UNKNOWN" and listing_url:
                        all_data.append({
                            "locality": locality,
                            "property_type": property_type,
                            "total_price": total_price,
                            "area_sqft": area_sqft,
                            "price_per_sqft": price_per_sqft,
                            "listing_url": listing_url,
                            "scrape_date": scrape_date,
                            "source": "magicbricks",
                        })

                    if len(all_data) >= target_count:
                        break
                except Exception:
                    continue

            logger.info("Page %d: collected %d items so far.", page, len(all_data))
            page += 1
            time.sleep(random.uniform(10, 15))

        except Exception as e:
            logger.error("Error at page %d: %s", page, e)
            break

    logger.info("Scraping finished. Total raw listings: %d", len(all_data))
    return all_data


# ── Data cleaning ────────────────────────────────────────────────────────────

def clean_listings(raw_data: list[dict]) -> list[dict]:
    """
    Apply cleaning rules (same logic as nagpur_real_estate_cleaned.py):
    - deduplicate
    - drop invalid prices / localities
    - normalize locality names
    - filter outlier price_per_sqft
    """
    if not raw_data:
        return []

    df = pd.DataFrame(raw_data)

    # Deduplicate by listing_url
    df = df.drop_duplicates(subset=["listing_url"])

    # Deduplicate by content
    df = df.drop_duplicates(subset=["total_price", "locality", "area_sqft"])

    # Drop rows with no price or locality
    df = df.dropna(subset=["total_price", "locality"])
    df = df[df["total_price"] > 0]

    # Clean locality names
    df["locality"] = df["locality"].apply(_clean_locality_name)
    df = df[df["locality"] != ""]

    # Ensure price_per_sqft exists
    mask = (df["price_per_sqft"] == 0) & (df["total_price"] > 0) & (df["area_sqft"] > 0)
    df.loc[mask, "price_per_sqft"] = (df.loc[mask, "total_price"] / df.loc[mask, "area_sqft"]).round(2)

    # Filter outliers
    df = df[(df["price_per_sqft"] >= 500) & (df["price_per_sqft"] <= 50000)]

    return df.to_dict(orient="records")


# ── Aggregation ──────────────────────────────────────────────────────────────

def compute_locality_snapshots(cleaned: list[dict]) -> list[dict]:
    """Aggregate cleaned listings into per-locality daily snapshots."""
    if not cleaned:
        return []

    df = pd.DataFrame(cleaned)
    summary = (
        df.groupby("locality")
        .agg(
            avg_price_per_sqft=("price_per_sqft", "mean"),
            median_price=("total_price", "median"),
            total_listings=("locality", "count"),
        )
        .reset_index()
    )
    summary["avg_price_per_sqft"] = summary["avg_price_per_sqft"].round(2)
    summary["median_price"] = summary["median_price"].round(0)
    summary["snapshot_date"] = date.today()
    summary["source"] = "magicbricks"

    return summary.to_dict(orient="records")


# ── Database insertion ───────────────────────────────────────────────────────

def save_to_db(cleaned: list[dict], snapshots: list[dict]) -> int:
    """
    Insert cleaned listings and locality snapshots into the database.
    Returns the number of new listings inserted.
    """
    session = get_session()
    inserted = 0
    try:
        # Insert raw listings (skip duplicates via listing_url + scrape_date)
        for row in cleaned:
            existing = (
                session.query(RawListing)
                .filter_by(listing_url=row["listing_url"], scrape_date=row["scrape_date"])
                .first()
            )
            if not existing:
                session.add(RawListing(**row))
                inserted += 1

        # Upsert locality snapshots
        for snap in snapshots:
            existing = (
                session.query(LocalitySnapshot)
                .filter_by(
                    locality=snap["locality"],
                    snapshot_date=snap["snapshot_date"],
                    source=snap["source"],
                )
                .first()
            )
            if existing:
                existing.avg_price_per_sqft = snap["avg_price_per_sqft"]
                existing.median_price = snap["median_price"]
                existing.total_listings = snap["total_listings"]
            else:
                session.add(LocalitySnapshot(**snap))

        session.commit()
        logger.info("DB: inserted %d new listings, upserted %d snapshots.", inserted, len(snapshots))
    except Exception as e:
        session.rollback()
        logger.error("DB insert failed: %s", e)
        raise
    finally:
        session.close()

    return inserted


# ── Full pipeline (single call to do everything) ─────────────────────────────

def run_scrape_pipeline(target_count: int = 300) -> dict:
    """
    End-to-end: scrape → clean → aggregate → save to DB.
    Returns a summary dict for the API response.
    """
    session = get_session()

    # Log the scrape run
    log = ScrapeLog(source="magicbricks", started_at=datetime.utcnow())
    session.add(log)
    session.commit()
    log_id = log.id

    try:
        # 1. Scrape
        raw = scrape_magicbricks(target_count=target_count)

        # 2. Clean
        cleaned = clean_listings(raw)

        # 3. Aggregate
        snapshots = compute_locality_snapshots(cleaned)

        # 4. Store
        new_count = save_to_db(cleaned, snapshots)

        # Update log
        log = session.get(ScrapeLog, log_id)
        log.finished_at = datetime.utcnow()
        log.listings_scraped = len(cleaned)
        log.status = "success"
        session.commit()

        return {
            "status": "success",
            "raw_scraped": len(raw),
            "after_cleaning": len(cleaned),
            "new_in_db": new_count,
            "localities": len(snapshots),
        }

    except Exception as e:
        log = session.get(ScrapeLog, log_id)
        log.finished_at = datetime.utcnow()
        log.status = "failed"
        log.error_message = str(e)
        session.commit()
        logger.error("Pipeline failed: %s", e)
        return {"status": "failed", "error": str(e)}
    finally:
        session.close()


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    result = run_scrape_pipeline(target_count=300)
    print(result)
