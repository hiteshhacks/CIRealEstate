#!/usr/bin/env python
# coding: utf-8

# In[16]:


import pandas as pd
df=pd.read_csv("nagpur_real_estate_cleaned.csv")
df.head()


# In[17]:


import plotly.express as px

expensive = (
    df.groupby("locality")["avg_price_per_sqft"]
      .mean()
      .sort_values(ascending=False)
      .head(5)
      .reset_index()
)

fig1 = px.bar(
    expensive,
    x="locality",
    y="avg_price_per_sqft",
    title="Top 5 Most Expensive Localities (Avg Price per Sqft)",
    labels={"avg_price_per_sqft": "Avg Price per Sqft"}
)

fig1.show()


# In[18]:


affordable = (
    df.groupby("locality")["avg_price_per_sqft"]
      .mean()
      .sort_values()
      .head(5)
      .reset_index()
)

fig2 = px.bar(
    affordable,
    x="locality",
    y="avg_price_per_sqft",
    title="Top 5 Most Affordable Localities (Avg Price per Sqft)",
    labels={"avg_price_per_sqft": "Avg Price per Sqft"}
)

fig2.show()


# In[19]:


avg_price = (
    df.groupby("locality")["avg_price_per_sqft"]
      .mean()
      .sort_values(ascending=False)
      .reset_index()
)

fig3 = px.bar(
    avg_price,
    x="locality",
    y="avg_price_per_sqft",
    title="Average Price per Sqft by Locality"
)

fig3.update_layout(xaxis_tickangle=-45)
fig3.show()


# In[20]:


fig4 = px.histogram(
    df,
    x="median_price",
    nbins=40,
    title="Distribution of Total Listing Prices"
)

fig4.show()


# In[21]:


listing_count = (
    df["locality"]
    .value_counts()
    .reset_index()
)

listing_count.columns = ["locality", "total_listings"]

fig5 = px.bar(
    listing_count,
    x="locality",
    y="total_listings",
    title="Number of Listings per Locality"
)

fig5.update_layout(xaxis_tickangle=-45)
fig5.show()


# In[ ]:




