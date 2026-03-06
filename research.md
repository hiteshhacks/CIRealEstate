# Research: Real-Time Real Estate Analytics Backend

## What Is This Project About?

This project is a **Real Estate Analytics Dashboard** for Nagpur city. It collects property listing data (prices, localities, area, property types) from real estate websites like MagicBricks, and then shows useful analytics — like which localities are expensive, which are affordable, how many listings are there, etc.

---

## The Problem: Everything Was Static

When the project was first built, it worked like this:

1. Someone runs `nagpur_data_scraping.py` **one time** manually
2. That script goes to MagicBricks website, collects ~300 property listings, and saves them into a CSV file (`nagpur_real_estate_raw.csv`)
3. Then `nagpur_real_estate_cleaned.py` is run to clean that data — remove duplicates, fix prices, normalize locality names — and save a cleaned version (`nagpur_real_estate_cleaned.csv`)
4. The backend (`backend.py`) reads these CSV files and serves the data through an API
5. The frontend (Streamlit) calls the API and displays charts

**The big problem?** The data never changes. Once those CSV files are created, the backend reads the same data forever. Even if property prices change tomorrow, the dashboard would still show yesterday's numbers. The data is **frozen in time**.

Also, the "time series" and "forecasting" features were using **simulated (fake) data** — the code was just generating random numbers around the average price and pretending that's a historical trend. The Prophet model was making predictions on this fake data, so the forecasts were meaningless.

---

## What We Did: Made It Real-Time

We converted the backend from reading static CSV files to reading from a **live SQLite database** that gets updated automatically through scheduled web scraping.

### In Simple Words

**Before:** Data is scraped once → saved to CSV → backend reads CSV → shows same data forever.

**After:** Data is scraped automatically every few hours → cleaned and saved to a database → backend reads from database → shows fresh/updated data always.

---

## How It Works Now (Step by Step)

### Step 1: The Database (`database.py`)

Instead of CSV files, we now use a **SQLite database** (a single file called `real_estate.db`). Think of it as an Excel workbook that lives inside one file and that Python can read/write very fast.

The database has **3 tables**:

#### Table 1: `raw_listings`
This stores every individual property listing exactly as it was scraped from the website.

| Column | What It Stores | Example |
|--------|---------------|---------|
| locality | The area/neighborhood name | DHARAMPETH |
| property_type | What kind of property | Flat, Villa, Plot |
| total_price | Full price of the property | 21900000 (₹2.19 Cr) |
| area_sqft | Size in square feet | 2126 |
| price_per_sqft | Price divided by area | 10299 |
| listing_url | Link to the listing on MagicBricks | https://magicbricks.com/... |
| source | Which website it came from | magicbricks |
| scrape_date | When we scraped it | 2026-02-25 |

#### Table 2: `locality_snapshots`
This stores **daily aggregated stats** per locality. Instead of storing every individual listing, this table summarizes: "On this date, DHARAMPETH had an average price of ₹10,299/sqft across 5 listings."

| Column | What It Stores | Example |
|--------|---------------|---------|
| locality | The area name | DHARAMPETH |
| avg_price_per_sqft | Average price per square foot | 10299.0 |
| median_price | Middle value of all prices | 21900000.0 |
| total_listings | How many listings we found | 5 |
| snapshot_date | Which date this is for | 2026-02-25 |

**Why this table matters:** Over time (days, weeks, months), this table builds up real historical data. On Feb 25, DHARAMPETH was ₹10,299/sqft. On March 1, maybe it's ₹10,500/sqft. On March 15, maybe ₹10,200/sqft. This gives us a **real price trend** — not simulated/fake data.

#### Table 3: `scrape_logs`
This tracks every time we run the scraper, so we know if our data is fresh or old.

| Column | What It Stores | Example |
|--------|---------------|---------|
| started_at | When the scrape started | 2026-03-01 12:00:00 |
| finished_at | When it finished | 2026-03-01 12:08:30 |
| listings_scraped | How many listings were collected | 245 |
| status | Did it work? | success / failed |

---

### Step 2: The Scraper (`scraper.py`)

This file combines two old scripts into one:
- The scraping logic from `nagpur_data_scraping.py` (going to MagicBricks and extracting data)
- The cleaning logic from `nagpur_real_estate_cleaned.py` (fixing prices, removing duplicates, normalizing locality names)

It works as a **pipeline** — one function call does everything:

```
scrape_magicbricks()       →  Goes to MagicBricks, collects raw listings
        ↓
clean_listings()           →  Removes duplicates, fixes prices, cleans locality names
        ↓
compute_locality_snapshots() → Aggregates: "DHARAMPETH = ₹10,299/sqft avg, 5 listings"
        ↓
save_to_db()               →  Inserts everything into the SQLite database
```

**What the scraper does in detail:**

1. Opens a web session to MagicBricks (like opening Chrome but in the background)
2. Goes to the property listing page for Nagpur
3. For each listing card on the page, it extracts:
   - Locality name (where the property is)
   - Property type (Flat, Villa, House, Plot)
   - Total price (converts "1.5 Cr" to 15000000)
   - Area in square feet
   - Price per square foot
   - URL of the listing
4. Moves to the next page, repeats (with 10-15 second delays to avoid being blocked)
5. After collecting ~300 listings, it cleans the data:
   - Removes duplicates (same URL or same price+locality+area)
   - Removes listings with missing prices or unknown localities
   - Normalizes locality names (uppercase, remove "ROAD", "AREA", etc.)
   - Filters out unrealistic prices (below ₹500/sqft or above ₹50,000/sqft)
6. Aggregates into daily locality-level stats
7. Saves everything into the database

**Why it's better than before:**
- Before: One script scrapes, saves CSV. Another script cleans, saves another CSV. Manual process.
- Now: One function does everything automatically. And it saves to a database, not CSV.

---

### Step 3: The Backend API (`backend.py`)

This is the FastAPI server that provides data to the frontend (or to anyone who asks).

**Before:** It loaded CSV files into memory once using `@lru_cache()` and served the same data forever.

**Now:** It queries the SQLite database on every request, so it always returns the latest data.

#### All API Endpoints (URLs you can visit)

**Data Endpoints:**

| Endpoint | Method | What It Returns |
|----------|--------|-----------------|
| `/localities` | GET | List of all locality names that have data |
| `/locality/{name}/summary` | GET | Average price, total listings, median price for a specific locality |
| `/locality/{name}/prices` | GET | All individual price-per-sqft values for a locality |
| `/locality/{name}/history` | GET | Price history across multiple scrape dates (real trend!) |
| `/top_localities` | GET | Top 5 most expensive + Top 5 most affordable localities |
| `/compare?localities=A,B,C` | GET | Side-by-side comparison of multiple localities |

**Scraping Endpoints:**

| Endpoint | Method | What It Does |
|----------|--------|--------------|
| `/scrape/trigger` | POST | Starts a fresh scrape in the background |
| `/scrape/status` | GET | Shows if data is fresh ("live"), recent, or old ("stale") |

**Download Endpoints:**

| Endpoint | Method | What It Returns |
|----------|--------|-----------------|
| `/download/listings` | GET | All raw listings as a CSV file download |
| `/download/snapshots` | GET | All locality snapshots as a CSV file download |

**Migration Endpoint:**

| Endpoint | Method | What It Does |
|----------|--------|--------------|
| `/seed` | POST | One-time: imports old CSV file data into the new database |

#### How "Data Freshness" Works

The `/scrape/status` endpoint tells you how old your data is:
- 🟢 **"live"** — Last scrape was less than 6 hours ago. Data is fresh.
- 🟡 **"recent"** — Last scrape was less than 24 hours ago. Data is fairly current.
- 🔴 **"stale"** — Last scrape was more than 24 hours ago. Data might be outdated.

This is possible because of the `scrape_logs` table — every time the scraper runs, it logs when it started and finished.

---

### Step 4: The Scheduler (`scheduler.py`)

This is a simple script that automatically runs the scraper at regular intervals.

- When you start it, it immediately runs one scrape
- Then it waits 6 hours (configurable) and runs again
- Repeats forever until you stop it

This means: if you leave `scheduler.py` running on your computer (or a server), your database will automatically get fresh data every 6 hours. No manual work needed.

**How to change the interval:** Set the environment variable `SCRAPE_INTERVAL_HOURS` before starting:
```bash
set SCRAPE_INTERVAL_HOURS=12    # scrape every 12 hours instead of 6
python scheduler.py
```

---

## File Structure

Here's what each file in the project does:

```
project/
│
│── database.py                    ← NEW: Database models (tables definition)
│── scraper.py                     ← NEW: Scrape + Clean + Save to DB pipeline
│── scheduler.py                   ← NEW: Auto-runs scraper every 6 hours
│── backend.py                     ← MODIFIED: Now queries database, not CSV files
│── requirements.txt               ← MODIFIED: Added new dependencies
│── real_estate.db                 ← NEW: The SQLite database file (auto-created)
│
│── streamlit_app.py               ← Frontend (not changed, out of scope)
│
│── nagpur_data_scraping.py        ← OLD: Original scraper (no longer used)
│── nagpur_real_estate_cleaned.py  ← OLD: Original cleaning script (no longer used)
│── nagpur_real_estate_raw.xls     ← OLD: Original raw data file
│── nagpur_real_estate_cleaned.xls ← OLD: Original cleaned data file
│── forecasting.py                 ← OLD: Prophet forecasting (not used right now)
│── prophet_app.py                 ← OLD: Prophet app (not used right now)
```

---

## How to Run Everything

### First Time Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start the API server
python -m uvicorn backend:app --host 0.0.0.0 --port 8000

# 3. Open a second terminal and seed the existing CSV data into the database
#    (this imports your old data so you have something to start with)
curl -X POST http://localhost:8000/seed
#    or in Python:
python -c "import requests; print(requests.post('http://localhost:8000/seed').json())"

# 4. Now visit http://localhost:8000/docs to see all endpoints
```

### Getting Fresh Data

```bash
# Option A: Trigger a single scrape via the API
curl -X POST http://localhost:8000/scrape/trigger

# Option B: Run the scraper directly
python scraper.py

# Option C: Start the auto-scheduler (scrapes every 6 hours, runs forever)
python scheduler.py
```

### Checking if Data is Fresh

```bash
curl http://localhost:8000/scrape/status
# Returns: {"status": "success", "freshness": "live", "listings_scraped": 245, ...}
```

---

## What Technologies We Used and Why

| Technology | Why We Used It |
|------------|---------------|
| **SQLite** | Simple database that lives in one file. No need to install MySQL or PostgreSQL. Perfect for a project this size. |
| **SQLAlchemy** | Python library that lets us talk to the database using Python code instead of writing raw SQL queries. Makes it easier to create tables, insert data, and query data. |
| **FastAPI** | The web framework for our API. It's fast, modern, and automatically generates the Swagger documentation page at `/docs`. |
| **BeautifulSoup** | Parses the HTML from MagicBricks website. When we download a page, BS4 helps us find specific elements (price, locality, area) inside the HTML. |
| **APScheduler** | Runs our scraper at fixed intervals (every 6 hours). Like a cron job but inside Python. |
| **Redis** (optional) | Caches API responses for 15 minutes so the same request doesn't hit the database repeatedly. If Redis is not installed, the API still works — just without caching. |

---

## Before vs After Comparison

| Aspect | Before (Static) | After (Real-Time) |
|--------|-----------------|-------------------|
| Data source | CSV files created once | SQLite database updated every 6 hours |
| How data is loaded | `pd.read_csv()` with `@lru_cache()` | SQLAlchemy database queries |
| Data freshness | Always the same (stale) | Fresh data every 6 hours |
| Historical trends | Simulated (random noise) | Real — built from daily snapshots over time |
| Scraping | Manual one-time run | Automatic scheduled runs |
| Adding new data | Re-run scripts manually, overwrite CSV | Automatic — new data is appended, old data is kept |
| Data cleaning | Separate script, manual step | Built into the scraper pipeline, automatic |

---

## What We Did NOT Do (Out of Scope for Now)

1. **Frontend changes** — The Streamlit frontend (`streamlit_app.py`) was not modified. It still talks to the same API endpoints, so it should mostly work as before. Some new endpoints (like `/locality/{name}/history` and `/scrape/status`) are available but the frontend doesn't use them yet.

2. **Price prediction / forecasting** — We removed Prophet and the ML prediction models for now because prediction needs months of historical data to be meaningful. The old forecasting was running on fake/simulated data, which made the predictions useless. Once enough real data has been collected (3-6 months of daily scrapes), we can add real prediction back.

3. **Multiple data sources** — Currently we only scrape MagicBricks. In the future, we can add scrapers for 99acres, Housing.com, etc. The database schema already has a `source` column to support this.

---

## How the Data Flows (Visual Summary)

```
                    EVERY 6 HOURS (scheduler.py)
                           │
                           ▼
┌─────────────────────────────────────────────┐
│           scraper.py                        │
│                                             │
│  1. Go to MagicBricks website               │
│  2. Collect ~300 property listings           │
│  3. Clean the data (remove duplicates,       │
│     fix prices, normalize locality names)    │
│  4. Aggregate into daily locality stats      │
│  5. Save everything to the database          │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│        real_estate.db (SQLite)              │
│                                             │
│  raw_listings table      → individual props │
│  locality_snapshots table → daily averages  │
│  scrape_logs table       → scrape history   │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│           backend.py (FastAPI)              │
│                                             │
│  Queries the database on each request       │
│  Returns JSON responses                     │
│  Endpoints: /localities, /summary,          │
│             /prices, /top_localities,        │
│             /compare, /history,              │
│             /scrape/trigger, /scrape/status   │
└──────────────────┬──────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────┐
│    Anyone can consume the API               │
│                                             │
│  • Browser (http://localhost:8000/docs)      │
│  • Streamlit frontend                        │
│  • Postman                                   │
│  • curl commands                             │
│  • Any other app                             │
└─────────────────────────────────────────────┘
```

---

## Key Takeaways

1. **We replaced static CSV files with a live database** — this is the single most important change. Everything else follows from this.

2. **We automated the scraping** — instead of running a script manually once, the scraper now runs automatically every 6 hours and adds new data to the database.

3. **We merged scraping + cleaning into one pipeline** — before, you had to run two scripts separately. Now, one function call (`run_scrape_pipeline()`) does everything.

4. **We kept full history** — every scrape adds new rows to the database. Old data is never deleted. This means over time, we build a real price history that can be used for actual analytics and (eventually) real predictions.

5. **We added data freshness tracking** — the API now tells you exactly when the last scrape happened and whether your data is fresh or stale.
