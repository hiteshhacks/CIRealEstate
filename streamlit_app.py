import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.express as px
import plotly.graph_objects as go
import logging

logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

st.set_page_config(page_title='Nagpur RE Forecast | FinVise', layout='wide')

API_URL = st.secrets.get("api_url", "http://localhost:8000")

# helper to call backend endpoints
@st.cache_data
def fetch_json(route, params=None):
    url = f"{API_URL}{route}"
    resp = requests.get(url, params=params)
    resp.raise_for_status()
    return resp.json()

@st.cache_data
def get_localities():
    return fetch_json("/localities")["localities"]

localities = get_localities()

# Sidebar navigation
page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Trend & Forecast", "Compare Localities", "Download Data"]
)

# --- Dashboard page ---
if page == "Dashboard":
    st.title("Nagpur Real Estate Dashboard")

    selected_locality = st.selectbox("Select Locality", localities)
    # metrics from backend
    metrics = fetch_json(f"/locality/{selected_locality}/summary")

    col1, col2, col3 = st.columns(3)
    col1.metric("Avg Price / Sqft", metrics["avg_price_per_sqft"])
    col2.metric("Total Listings", metrics["total_listings"])
    col3.metric("Median Price", metrics["median_price"])

    # distribution data
    price_data = fetch_json(f"/locality/{selected_locality}/prices")["prices"]
    st.subheader("Price Distribution")
    fig = px.histogram(
        pd.DataFrame({"avg_price_per_sqft": price_data}),
        x="avg_price_per_sqft",
        nbins=30,
        title=f"{selected_locality} Price Distribution"
    )
    st.plotly_chart(fig, use_container_width=True)

    # top/bottom localities
    st.subheader("Top 5 Expensive vs Affordable Localities")
    tb = fetch_json("/top_localities")
    top5 = pd.DataFrame(tb["top5"])
    bottom5 = pd.DataFrame(tb["bottom5"])

    col1, col2 = st.columns(2)
    with col1:
        fig_top = px.bar(top5, x="locality", y="avg_price_per_sqft", title="Top 5 Expensive")
        st.plotly_chart(fig_top, use_container_width=True)
    with col2:
        fig_bottom = px.bar(bottom5, x="locality", y="avg_price_per_sqft", title="Top 5 Affordable")
        st.plotly_chart(fig_bottom, use_container_width=True)

# --- Trend & Forecast page ---
elif page == "Trend & Forecast":
    st.title("Price Trend & Forecast")

    selected_locality = st.selectbox("Select Locality", localities)
    forecast_days = st.slider("Forecast Days", 30, 180, 90)

    ts = fetch_json(f"/locality/{selected_locality}/timeseries")
    ts_df = pd.DataFrame(ts["history"])  # columns ds,y

    st.subheader("Historical Trend")
    fig_hist = px.line(ts_df, x="ds", y="y", title=f"{selected_locality} Historical Trend")
    st.plotly_chart(fig_hist, use_container_width=True)

    forecast_resp = fetch_json(f"/locality/{selected_locality}/forecast", params={"days": forecast_days})
    forecast_df = pd.DataFrame(forecast_resp["forecast"])

    st.subheader("Forecast with Confidence Interval")
    fig_forecast = go.Figure()
    fig_forecast.add_trace(go.Scatter(x=ts_df["ds"], y=ts_df["y"], mode="lines", name="Historical"))
    fig_forecast.add_trace(go.Scatter(x=forecast_df["ds"], y=forecast_df["yhat"], mode="lines", name="Forecast"))
    fig_forecast.add_trace(go.Scatter(x=forecast_df["ds"], y=forecast_df["yhat_upper"], line=dict(width=0), showlegend=False))
    fig_forecast.add_trace(go.Scatter(x=forecast_df["ds"], y=forecast_df["yhat_lower"], fill="tonexty", mode="lines", line=dict(width=0), name="Confidence Interval"))
    st.plotly_chart(fig_forecast, use_container_width=True)

    fs = fetch_json("/forecast_summary")["forecast_summary"]
    st.subheader("Forecast Summary")
    st.dataframe(pd.DataFrame(fs).rename(columns={"growth_pct": "% Growth"}), use_container_width=True)

# --- Compare Localities page ---
elif page == "Compare Localities":
    st.title("Compare Localities")

    selected_locs = st.multiselect("Select Localities to Compare", localities, default=localities[:2])
    if selected_locs:
        comp = fetch_json("/compare", params={"localities": ",".join(selected_locs)})
        comp_avg = pd.DataFrame(comp["comp_avg"])
        stats_table = pd.DataFrame(comp["stats_table"])

        fig = px.bar(comp_avg, x="locality", y="avg_price_per_sqft", title="Average Price per Sqft Comparison")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Locality Statistics")
        st.dataframe(stats_table, use_container_width=True)
    else:
        st.info("Select at least one locality to compare.")

# --- Download Data page ---
elif page == "Download Data":
    st.title("⬇ Download Data")
    st.markdown("You can retrieve the raw files directly via the API endpoints.")
    st.write(
        f"Cleaned data: {API_URL}/download/cleaned",
        unsafe_allow_html=True
    )
    st.write(
        f"Forecast summary: {API_URL}/download/forecast",
        unsafe_allow_html=True
    )
    st.success("Use the links above or curl them to download files.")
