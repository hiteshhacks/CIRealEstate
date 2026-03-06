"""
Real Estate Analytics API — backed by a live database.

All data comes from the SQLite database populated by scraper.py.
No more static CSV files.
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from sqlalchemy import func, desc
import pandas as pd
import json
import os
import redis
import logging
from datetime import datetime, date

from database import get_session, RawListing, LocalitySnapshot, ScrapeLog

logger = logging.getLogger(__name__)

app = FastAPI(title="Real Estate Analytics API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Redis (optional cache) ───────────────────────────────────────────────────

_redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
try:
    redis_client = redis.from_url(_redis_url)
    redis_client.ping()
except Exception:
    redis_client = None

CACHE_TTL = 60 * 15  # 15 minutes


def _cache_get(key: str):
    if not redis_client:
        return None
    try:
        val = redis_client.get(key)
        return json.loads(val) if val else None
    except Exception:
        return None


def _cache_set(key: str, value, ttl: int = CACHE_TTL):
    if not redis_client:
        return
    try:
        redis_client.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception:
        pass


# ── Helper: latest snapshot date ─────────────────────────────────────────────

def _latest_snapshot_date(session) -> date | None:
    """Return the most recent snapshot_date in the DB."""
    row = (
        session.query(func.max(LocalitySnapshot.snapshot_date))
        .scalar()
    )
    return row


# ── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/localities")
def get_localities():
    """Return list of all localities that have data."""
    cached = _cache_get("localities")
    if cached:
        return cached

    session = get_session()
    try:
        latest = _latest_snapshot_date(session)
        if latest is None:
            raise HTTPException(status_code=404, detail="No data in database. Run a scrape first.")

        rows = (
            session.query(LocalitySnapshot.locality)
            .filter(LocalitySnapshot.snapshot_date == latest)
            .distinct()
            .all()
        )
        localities = sorted([r[0] for r in rows])
        result = {"localities": localities, "data_date": str(latest)}
        _cache_set("localities", result)
        return result
    finally:
        session.close()


@app.get("/locality/{locality}/summary")
def locality_summary(locality: str):
    """Per-locality metrics from the latest snapshot."""
    cache_key = f"summary:{locality}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    session = get_session()
    try:
        latest = _latest_snapshot_date(session)
        snap = (
            session.query(LocalitySnapshot)
            .filter_by(locality=locality, snapshot_date=latest)
            .first()
        )
        if not snap:
            raise HTTPException(status_code=404, detail="Locality not found")

        result = {
            "avg_price_per_sqft": round(snap.avg_price_per_sqft, 2),
            "total_listings": snap.total_listings,
            "median_price": round(snap.median_price, 2),
            "data_date": str(snap.snapshot_date),
        }
        _cache_set(cache_key, result)
        return result
    finally:
        session.close()


@app.get("/locality/{locality}/prices")
def locality_prices(locality: str):
    """Return all individual price_per_sqft values for a locality from the latest scrape."""
    session = get_session()
    try:
        latest = _latest_snapshot_date(session)
        rows = (
            session.query(RawListing.price_per_sqft)
            .filter(RawListing.locality == locality, RawListing.scrape_date == latest)
            .all()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Locality not found")

        prices = [r[0] for r in rows if r[0] and r[0] > 0]
        return {"prices": prices, "data_date": str(latest)}
    finally:
        session.close()


@app.get("/top_localities")
def top_bottom_localities():
    """Top 5 expensive and top 5 affordable localities."""
    cached = _cache_get("top_localities")
    if cached:
        return cached

    session = get_session()
    try:
        latest = _latest_snapshot_date(session)
        if latest is None:
            raise HTTPException(status_code=404, detail="No data yet")

        snaps = (
            session.query(LocalitySnapshot)
            .filter_by(snapshot_date=latest)
            .order_by(LocalitySnapshot.avg_price_per_sqft)
            .all()
        )

        records = [
            {"locality": s.locality, "avg_price_per_sqft": round(s.avg_price_per_sqft, 2)}
            for s in snaps
        ]
        bottom5 = records[:5]
        top5 = records[-5:]

        result = {"top5": top5, "bottom5": bottom5, "data_date": str(latest)}
        _cache_set("top_localities", result)
        return result
    finally:
        session.close()


@app.get("/compare")
def compare_localities(localities: str):
    """Compare multiple localities. Pass comma-separated names: ?localities=A,B,C"""
    session = get_session()
    try:
        latest = _latest_snapshot_date(session)
        locs = [l.strip() for l in localities.split(",") if l.strip()]

        snaps = (
            session.query(LocalitySnapshot)
            .filter(
                LocalitySnapshot.locality.in_(locs),
                LocalitySnapshot.snapshot_date == latest,
            )
            .all()
        )
        if not snaps:
            raise HTTPException(status_code=404, detail="No matching localities")

        comp_avg = [
            {"locality": s.locality, "avg_price_per_sqft": round(s.avg_price_per_sqft, 2)}
            for s in snaps
        ]
        stats_table = [
            {
                "locality": s.locality,
                "avg_price_sqft": round(s.avg_price_per_sqft, 2),
                "median_price": round(s.median_price, 2),
                "listings": s.total_listings,
            }
            for s in snaps
        ]
        return {
            "comp_avg": comp_avg,
            "stats_table": stats_table,
            "data_date": str(latest),
        }
    finally:
        session.close()


@app.get("/locality/{locality}/history")
def locality_history(locality: str):
    """
    Return the full price history for a locality across all scrape dates.
    This is the REAL historical data — one row per snapshot_date.
    """
    session = get_session()
    try:
        rows = (
            session.query(LocalitySnapshot)
            .filter_by(locality=locality)
            .order_by(LocalitySnapshot.snapshot_date)
            .all()
        )
        if not rows:
            raise HTTPException(status_code=404, detail="Locality not found or no history")

        history = [
            {
                "date": str(r.snapshot_date),
                "avg_price_per_sqft": round(r.avg_price_per_sqft, 2),
                "median_price": round(r.median_price, 2),
                "total_listings": r.total_listings,
            }
            for r in rows
        ]
        return {"locality": locality, "history": history}
    finally:
        session.close()


# ── Scrape management ────────────────────────────────────────────────────────

@app.post("/scrape/trigger")
def trigger_scrape(background_tasks: BackgroundTasks, target_count: int = 300):
    """
    Trigger a fresh scrape in the background.
    Returns immediately; the scrape runs asynchronously.
    """
    from scraper import run_scrape_pipeline

    # Clear cache so next request gets fresh data
    if redis_client:
        try:
            redis_client.flushdb()
        except Exception:
            pass

    background_tasks.add_task(run_scrape_pipeline, target_count)
    return {"message": "Scrape started in background", "target_count": target_count}


@app.get("/scrape/status")
def scrape_status():
    """Return info about the most recent scrape run for freshness monitoring."""
    session = get_session()
    try:
        log = (
            session.query(ScrapeLog)
            .order_by(desc(ScrapeLog.id))
            .first()
        )
        if not log:
            return {"status": "no_scrapes_yet", "freshness": "stale"}

        result = {
            "last_scrape_id": log.id,
            "source": log.source,
            "status": log.status,
            "started_at": str(log.started_at) if log.started_at else None,
            "finished_at": str(log.finished_at) if log.finished_at else None,
            "listings_scraped": log.listings_scraped,
            "error": log.error_message,
        }

        # compute freshness
        if log.finished_at:
            age_hours = (datetime.utcnow() - log.finished_at).total_seconds() / 3600
            if age_hours < 6:
                result["freshness"] = "live"        # 🟢
            elif age_hours < 24:
                result["freshness"] = "recent"      # 🟡
            else:
                result["freshness"] = "stale"       # 🔴
        else:
            result["freshness"] = "running" if log.status == "running" else "stale"

        return result
    finally:
        session.close()


@app.get("/download/listings")
def download_listings():
    """Download all raw listings as CSV."""
    session = get_session()
    try:
        rows = session.query(RawListing).all()
        if not rows:
            raise HTTPException(status_code=404, detail="No data")

        df = pd.DataFrame([{
            "locality": r.locality,
            "property_type": r.property_type,
            "total_price": r.total_price,
            "area_sqft": r.area_sqft,
            "price_per_sqft": r.price_per_sqft,
            "listing_url": r.listing_url,
            "source": r.source,
            "scrape_date": str(r.scrape_date),
        } for r in rows])

        csv_bytes = df.to_csv(index=False).encode()
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=listings.csv"},
        )
    finally:
        session.close()


@app.get("/download/snapshots")
def download_snapshots():
    """Download all locality snapshots as CSV."""
    session = get_session()
    try:
        rows = session.query(LocalitySnapshot).all()
        if not rows:
            raise HTTPException(status_code=404, detail="No data")

        df = pd.DataFrame([{
            "locality": r.locality,
            "avg_price_per_sqft": r.avg_price_per_sqft,
            "median_price": r.median_price,
            "total_listings": r.total_listings,
            "snapshot_date": str(r.snapshot_date),
            "source": r.source,
        } for r in rows])

        csv_bytes = df.to_csv(index=False).encode()
        return Response(
            content=csv_bytes,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=snapshots.csv"},
        )
    finally:
        session.close()


# ── Seed existing CSV data into DB (one-time migration helper) ───────────────

@app.post("/seed")
def seed_from_csv():
    """
    One-time helper: import existing CSV/XLS data into the database
    so you don't lose your original data.
    """
    from database import init_db
    init_db()

    session = get_session()
    imported = 0
    try:
        # Try to find the cleaned data file
        for fname in ["nagpur_real_estate_cleaned.xls", "nagpur_real_estate_cleaned.csv"]:
            if os.path.exists(fname):
                df = pd.read_csv(fname)
                for _, row in df.iterrows():
                    snap = LocalitySnapshot(
                        locality=row.get("locality", ""),
                        avg_price_per_sqft=row.get("avg_price_per_sqft", 0),
                        median_price=row.get("median_price", 0),
                        total_listings=int(row.get("total_listings", 0)),
                        snapshot_date=pd.to_datetime(row.get("scrape_date", date.today())).date(),
                        source="csv_seed",
                    )
                    session.add(snap)
                    imported += 1
                break

        # Try to find the raw data file
        seen_urls = set()
        for fname in ["nagpur_real_estate_raw.xls", "nagpur_real_estate_raw.csv"]:
            if os.path.exists(fname):
                df = pd.read_csv(fname)
                for _, row in df.iterrows():
                    url = str(row.get("listing_url", ""))
                    sd = pd.to_datetime(row.get("scrape_date", date.today())).date()
                    key = (url, str(sd))
                    if not url or key in seen_urls:
                        continue
                    seen_urls.add(key)
                    listing = RawListing(
                        locality=row.get("locality", ""),
                        property_type=row.get("property_type", ""),
                        total_price=row.get("total_price", 0),
                        area_sqft=row.get("area_sqft", 0),
                        price_per_sqft=row.get("price_per_sqft", 0),
                        listing_url=url,
                        source="csv_seed",
                        scrape_date=sd,
                    )
                    session.add(listing)
                    imported += 1
                break

        session.commit()
        return {"message": f"Seeded {imported} rows from CSV files into the database."}
    except Exception as e:
        session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        session.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
