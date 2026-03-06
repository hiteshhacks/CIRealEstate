#!/usr/bin/env python
# coding: utf-8

# In[32]:


from prophet import Prophet
import pandas as pd
import numpy as np


def create_simulated_timeseries(df_locality, days=120):
    current_price = df_locality["avg_price_per_sqft"].mean()

    if pd.isna(current_price) or current_price <= 0:
        return None

    dates = pd.date_range(end=pd.Timestamp.today(), periods=days)

    trend = np.linspace(0, current_price * 0.05, days)
    noise = np.random.normal(0, current_price * 0.02, days)

    prices = current_price + trend + noise

    return pd.DataFrame({"ds": dates, "y": prices})


def calculate_growth(current_price, forecast_price):
    if pd.isna(current_price) or current_price <= 0:
        return 0
    return ((forecast_price - current_price) / current_price) * 100


forecast_summaries = []

for loc in df["locality"].unique():

    df_loc = df[df["locality"] == loc]

    ts_data = create_simulated_timeseries(df_loc)

    if ts_data is None or len(ts_data) < 5:
        continue

    model = Prophet()
    model.fit(ts_data)

    future = model.make_future_dataframe(periods=90)
    forecast = model.predict(future)

    current_price = ts_data["y"].iloc[-1]
    forecast_price = forecast["yhat"].iloc[-1]

    growth = calculate_growth(current_price, forecast_price)

    forecast_summaries.append({
        "locality": loc,
        "current_price": round(current_price, 2),
        "forecast_price": round(forecast_price, 2),
        "%_growth": round(growth, 2),
        "trend": "Upward" if growth > 0 else "Downward"
    })


forecast_summary_df = pd.DataFrame(forecast_summaries)


if len(forecast_summary_df) == 0:
    print("No forecasts generated. Check data.")
else:
    forecast_summary_df = forecast_summary_df.sort_values(
        by="%_growth", ascending=False
    ).reset_index(drop=True)

forecast_summary_df.head()





compare_stats = (
    df.groupby("locality")
    .agg(
        avg_price_sqft=("avg_price_per_sqft", "mean"),
        median_price=("median_price", "median"),
        listings=("locality", "count")
    )
    .reset_index()
)

compare_stats.head()



forecast_summary_df.to_csv("forecast_summary.csv", index=False)

locality_stats.to_csv("locality_stats.csv", index=False)


# In[33]:


from IPython.display import FileLink
FileLink("forecast_summary.csv")  # it gets downloaded as xls file in the device 


# In[34]:


FileLink("locality_stats.csv")


# In[ ]:




