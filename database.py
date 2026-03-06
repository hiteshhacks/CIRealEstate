"""
Database models and setup for the Real Estate Analytics platform.
Uses SQLite via SQLAlchemy for storing scraped listings and aggregated locality stats.
"""

from sqlalchemy import (
    create_engine, Column, Integer, Float, String, DateTime, Date, 
    UniqueConstraint, Index
)
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, date
import os

# ---------------------------------------------------------------------------
# Engine & Session
# ---------------------------------------------------------------------------

DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///real_estate.db")
engine = create_engine(DB_PATH, echo=False, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class RawListing(Base):
    """Individual property listings as scraped from sources."""
    __tablename__ = "raw_listings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    locality = Column(String, nullable=False, index=True)
    property_type = Column(String)
    total_price = Column(Float)
    area_sqft = Column(Float)
    price_per_sqft = Column(Float)
    listing_url = Column(String)
    source = Column(String, default="magicbricks")          # magicbricks / 99acres / etc.
    scrape_date = Column(Date, default=date.today, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Avoid inserting exact duplicate listings in a single scrape run
    __table_args__ = (
        UniqueConstraint("listing_url", "scrape_date", name="uq_listing_per_day"),
    )


class LocalitySnapshot(Base):
    """Daily aggregated stats per locality (computed after each scrape)."""
    __tablename__ = "locality_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    locality = Column(String, nullable=False, index=True)
    avg_price_per_sqft = Column(Float)
    median_price = Column(Float)
    total_listings = Column(Integer)
    source = Column(String, default="magicbricks")
    snapshot_date = Column(Date, default=date.today, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("locality", "snapshot_date", "source", name="uq_locality_snapshot"),
    )


class ScrapeLog(Base):
    """Track each scrape run for data-freshness monitoring."""
    __tablename__ = "scrape_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String, default="magicbricks")
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime)
    listings_scraped = Column(Integer, default=0)
    status = Column(String, default="running")              # running / success / failed
    error_message = Column(String)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def init_db():
    """Create all tables if they don't exist yet."""
    Base.metadata.create_all(bind=engine)


def get_session():
    """Return a new database session (caller must close it)."""
    return SessionLocal()


# Auto-create tables on import
init_db()
