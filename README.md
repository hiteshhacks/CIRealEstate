# 🏠 Real Estate Analytics & Forecasting Dashboard

An end-to-end data science project that scrapes real estate listings, performs data cleaning and analysis, builds price forecasting using Facebook Prophet, and presents insights through an interactive Streamlit dashboard.

---

# 📌 Project Overview

This project analyzes residential real estate trends in Nagpur by:

- Scraping property listing data
- Cleaning and transforming raw data
- Performing exploratory data analysis (EDA)
- Forecasting price per square foot using Prophet
- Building an interactive multi-page Streamlit dashboard

The application enables users to:

✔ View locality-wise price metrics  
✔ Compare different localities  
✔ Visualize price distributions  
✔ Forecast future price trends  
✔ Download cleaned datasets  

---

# 🧰 Tech Stack

- Python
- Pandas & NumPy
- Plotly (visualization)
- Facebook Prophet (time-series forecasting)
- Streamlit (web dashboard)
- BeautifulSoup / Requests (web scraping)
- Jupyter Notebook (data processing)

---

# 📂 Project Structure
```bash
nagpur-re-forecast/
│
├── app.py 
├── requirements.txt
├── README.md
└── prophet_for_app.py
│
├── data/
│ ├── nagpur_real_estate_cleaned.xls
│ ├── nagpur_real_estate_raw.xls
│ ├── forecast_summary.xls
│ ├── locality_stats.xls
│
│
├── notebooks/
│ └── nagpur_real_estate_cleaned.py
│ └── nagpur_real_estate_eda.py
│
│
└── nagpur_data_scraping.py

```
---


---

# 🧪 Data Pipeline

## 1️⃣ Web Scraping
Property data was collected from:

- MagicBricks
- 99acres
- Housing.com

Fields scraped:

- Locality  
- Property type  
- Price  
- Area (sqft)  
- Price per sqft  
- Scrape date  

---

## ⚠️ Challenges Faced During Scraping


Scraping MagicBricks using BeautifulSoup was challenging due to:

-Dynamic content loading: Many listings are rendered via JavaScript, so they were not available in the static HTML fetched using requests.

-Frequent HTML structure changes with deeply nested <div> elements and non-semantic class names, which made selectors unstable.

-Pagination handling required manual URL parameter modification and validation of each response.

-Bot detection (HTTP 403 errors) on repeated requests, which was mitigated using custom headers and time delays.

-Inconsistent data formats (₹, Lac, Crore; sqft vs sqyrd) that required extensive cleaning and normalization.

Scraping was performed at a low request rate and strictly for academic purposes.
---

# 🔄 Data Preprocessing

- Converted price strings → numeric
- Standardized area units → sqft
- Removed duplicates and missing values
- Created `avg_price_per_sqft`
- Created locality-level aggregated statistics

Output datasets:

- `nagpur_real_estate_cleaned.csv` → row-level data  
- `locality_stats.csv` → metrics for dashboard  
- `forecast_summary.csv` → Prophet forecast output  

---

# 📊 Forecasting Approach

Since scraped data is cross-sectional (not true time-series):

- Simulated locality-wise time series
- Applied **Facebook Prophet**
- Generated:
  - Trend
  - Forecast
  - Confidence intervals
  - Growth percentage

Forecast summary includes:

- Current price
- Forecasted price
- % growth
- Trend direction

---

# 🌐 Streamlit Dashboard Features

## 🧭 Page 1 — Dashboard
- Locality selection
- Metric cards:
  - Avg price per sqft
  - Total listings
  - Median price
- Price distribution histogram
- Top 5 expensive vs affordable localities

---

## 📈 Page 2 — Trend & Forecast
- Historical trend (simulated time series)
- Prophet forecast with confidence interval
- Forecast summary table

---

## 🏙 Page 3 — Compare Localities
- Multi-select localities
- Bar chart comparison of avg price per sqft
- Locality statistics table

---

## ⬇ Page 4 — Download Data
- Download cleaned dataset
- Download forecast summary

---

# ▶️ How to Run the Project

## 1️⃣ Clone the repository

```bash
git clone https://github.com/your-username/nagpur-real-estate-project.git
cd nagpur-real-estate-project
```
## 2️⃣ Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Mac
```
## 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

## 4️⃣ Run Streamlit app
```bash
streamlit run app.py
```

---

# 📊 Sample Insights

Dharampeth and Civil Lines show higher price per sqft

Emerging localities show higher forecast growth

Affordable zones provide better investment potential

---
📜 License

This project is for academic and educational purposes only.
Scraped data is used strictly for analysis and not for commercial use.
---
# 📂Documentation 
![pdf](documentation/documentation.pdf)

---
