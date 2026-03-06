#!/usr/bin/env python
# coding: utf-8

# In[71]:


import pandas as pd
import numpy as np
import re


# In[72]:


df = pd.read_csv("nagpur_real_estate_raw.csv")
df.head()


# In[73]:


if "url" in df.columns:
    df = df.drop_duplicates(subset=["url"])


# In[74]:


len(df)


# In[75]:


df = df.drop_duplicates(subset=["total_price", "locality", "area_sqft"])


# In[76]:


len(df)


# In[77]:


df.isnull().sum()


# In[78]:


df = df.dropna(subset=["total_price", "locality"])


# In[79]:


len(df)


# In[80]:


def clean_price(price):
    if pd.isna(price):
        return np.nan

    price = str(price).replace("₹", "").replace(",", "").strip().lower()

    # Handle Crore
    if "cr" in price:
        value = float(re.findall(r"\d+\.?\d*", price)[0])
        return value * 10000000  

    # Handle Lakh
    elif "lac" in price or "lakh" in price:
        value = float(re.findall(r"\d+\.?\d*", price)[0])
        return value * 100000

    else:
        try:
            return float(re.findall(r"\d+\.?\d*", price)[0])
        except:
            return np.nan


# In[81]:


df["total_price"] = df["total_price"].apply(clean_price)


# In[82]:


df.head()


# In[83]:


def clean_area(area):
    if pd.isna(area):
        return np.nan

    area = str(area).replace(",", "").lower()

    match = re.findall(r"\d+\.?\d*", area)
    if match:
        return float(match[0])
    return np.nan


# In[84]:


df["area_sqft"] = df["area_sqft"].apply(clean_area)


# In[85]:


df.head()


# In[86]:


df['locality']


# In[87]:


df['locality'].value_counts()


# In[88]:


def clean_locality(locality):
    if pd.isna(locality):
        return None

    locality = str(locality)
    locality = locality.upper()

    # Remove unwanted words
    unwanted_words = [
        "AREA", "NAGPUR", "CITY", "DISTRICT", 
        "MAHARASHTRA", "ROAD", "PHASE", 
        "NEAR", "OPP", "OPPOSITE"
    ]

    for word in unwanted_words:
        locality = locality.replace(word, "")

    # Remove numbers
    locality = re.sub(r"\d+", "", locality)

    # Remove special characters
    locality = re.sub(r"[^A-Z\s]", "", locality)

    # Remove extra spaces
    locality = re.sub(r"\s+", " ", locality).strip()

    return locality


# In[89]:


df["locality"] = df["locality"].apply(clean_locality)


# In[90]:


df.head()


# In[91]:


len(df)


# In[92]:


df = df[df["locality"] != ""]


# In[93]:


len(df)


# In[94]:


if "price_per_sqft" in df.columns:
    df["price_per_sqft"] = df["price_per_sqft"].fillna(
        df["total_price"] / df["area_sqft"] )


# In[95]:


df['price_per_sqft'].isnull().sum()


# In[96]:


df = df[
    (df["price_per_sqft"] >= 500) &
    (df["price_per_sqft"] <= 50000)
]


# In[97]:


locality_summary = (
    df.groupby("locality")
      .agg(
          avg_price_per_sqft=("price_per_sqft", "mean"),
          median_price=("total_price", "median"),
          total_listings=("locality", "count")
      )
      .reset_index()
)


# In[99]:


from datetime import datetime
locality_summary["scrape_date"] = datetime.today().date()


# In[100]:


locality_summary["avg_price_per_sqft"] = locality_summary["avg_price_per_sqft"].round(2)
locality_summary["median_price"] = locality_summary["median_price"].round(0)


# In[101]:


locality_summary.to_csv("nagpur_real_estate_cleaned.csv", index=False)

locality_summary.head()


# In[103]:


from IPython.display import FileLink
FileLink("nagpur_real_estate_cleaned.csv")


# In[ ]:




