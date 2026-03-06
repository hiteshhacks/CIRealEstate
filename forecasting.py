#!/usr/bin/env python
# coding: utf-8

# In[54]:


#get_ipython().system(' pip install prophet')


# In[55]:


import pandas as pd
import numpy as np
from prophet import Prophet
import plotly.graph_objects as go

df = pd.read_csv("nagpur_real_estate_cleaned.csv")


# In[56]:


# Simulate time series (last 180 days)
df["scrape_date"] = pd.to_datetime(df["scrape_date"])

df = df.sort_values("scrape_date")
ts_data = (
    df.groupby(["scrape_date", "locality"])["avg_price_per_sqft"]
      .mean()
      .reset_index()
)


# In[57]:


top_localities = (
    df["locality"]
    .value_counts()
    .head(4)
    .index
)

top_localities


# In[58]:


def create_simulated_timeseries(df_locality, days=120):
    
    current_price = df_locality["avg_price_per_sqft"].mean()
    
    dates = pd.date_range(end=pd.Timestamp.today(), periods=days)
    
    trend = np.linspace(0, current_price * 0.05, days)
    noise = np.random.normal(0, current_price * 0.02, days)
    
    prices = current_price + trend + noise
    
    ts = pd.DataFrame({
        "ds": dates,
        "y": prices
    })
    
    return ts


# In[59]:


from prophet import Prophet
import plotly.graph_objects as go

forecast_summary = []

for loc in top_localities:
    
    data_loc_raw = df[df["locality"] == loc]
    
    data_loc = create_simulated_timeseries(data_loc_raw, days=120)

  
    model = Prophet()
    model.fit(data_loc)

    future = model.make_future_dataframe(periods=90)
    forecast = model.predict(future)


    fig_hist = go.Figure()

    fig_hist.add_trace(go.Scatter(
        x=data_loc["ds"],
        y=data_loc["y"],
        mode='lines',
        name='Historical Avg Price'
    ))

    fig_hist.update_layout(
        title=f"{loc} — Historical Price Trend (₹/sqft)",
        xaxis_title="Date",
        yaxis_title="Avg Price per Sqft"
    )

    fig_hist.show()


    fig_forecast = go.Figure()

    # Forecast line
    fig_forecast.add_trace(go.Scatter(
        x=forecast["ds"],
        y=forecast["yhat"],
        mode='lines',
        name='Forecast'
    ))

    # Upper bound
    fig_forecast.add_trace(go.Scatter(
        x=forecast["ds"],
        y=forecast["yhat_upper"],
        mode='lines',
        line=dict(width=0),
        showlegend=False
    ))

    # Lower bound (fill area)
    fig_forecast.add_trace(go.Scatter(
        x=forecast["ds"],
        y=forecast["yhat_lower"],
        fill='tonexty',
        mode='lines',
        line=dict(width=0),
        name='Confidence Interval'
    ))

    fig_forecast.update_layout(
        title=f"{loc} — 90-Day Price Forecast (₹/sqft)",
        xaxis_title="Date",
        yaxis_title="Forecasted Price per Sqft"
    )

    fig_forecast.show()


    current_price = data_loc["y"].iloc[-1]
    forecast_price = forecast["yhat"].iloc[-1]

    growth = ((forecast_price - current_price) / current_price) * 100

    if growth > 7:
        trend_label = "↑ Rising"
    elif growth > 2:
        trend_label = "↑ Stable"
    elif growth < -2:
        trend_label = "↓ Falling"
    else:
        trend_label = "→ Flat"

    forecast_summary.append([
        loc,
        round(current_price, 2),
        round(forecast_price, 2),
        round(growth, 2),
        trend_label
    ])


# In[60]:


forecast_df = pd.DataFrame(
    forecast_summary,
    columns=[
        "Locality",
        "Current Avg Price (₹/sqft)",
        "Forecasted Price (₹/sqft)",
        "% Growth",
        "Trend"
    ]
)

forecast_df


# In[61]:


forecast_df.shape


# In[ ]:




