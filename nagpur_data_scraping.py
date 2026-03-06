#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import random
import re
from datetime import datetime


# In[7]:


City = 'Nagpur'
project_dir = './Real_estate_Nagpur_MB/'

def get_headers(referer=None):
    base_headers = {
        'authority': 'www.magicbricks.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.9',
        'cache-control': 'no-cache',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }
    if referer:
        base_headers['referer'] = referer
    return base_headers

def setup_directories():
    path = os.path.join(project_dir, f'Data/{City}/Flats/')
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def clean_numeric_value(text):
    if not text or "N/A" in text or "Call for Price" in text:
        return 0
    
    text = text.lower().replace(',', '').strip()
    
    # Handle Price units
    multiplier = 1
    if 'lac' in text:
        multiplier = 100000
    elif 'cr' in text or 'crore' in text:
        multiplier = 10000000
        
    # Extract decimal or integer
    match = re.search(r"(\d+\.?\d*)", text)
    if match:
        return int(float(match.group(1)) * multiplier)
    return 0

def scrape_nagpur_magicbricks(target_count=500):
    output_folder = setup_directories()
    all_data = []
    scrape_date = datetime.now().strftime("%Y-%m-%d")
    session = requests.Session()
    
    print("Initializing session...")
    try:
        session.get("https://www.magicbricks.com/", headers=get_headers(), timeout=15)
        time.sleep(random.uniform(2, 4))
    except: 
        print("Initial session warm-up failed, continuing anyway...")

    print(f"Starting Nagpur Scrape (Magicbricks) | Target: All listed (up to {target_count})")

    page_number = 1
    while len(all_data) < target_count:
        url = f'https://www.magicbricks.com/property-for-sale/residential-real-estate?&proptype=Multistorey-Apartment,Builder-Floor-Apartment,Penthouse,Studio-Apartment,Residential-House,Villas,Residential-Plot&cityName={City}&page={page_number}'
        referer = "https://www.magicbricks.com/" if page_number == 1 else f'https://www.magicbricks.com/property-for-sale/residential-real-estate?&cityName={City}&page={page_number-1}'
        
        try:
            response = session.get(url, headers=get_headers(referer), timeout=25)
            if response.status_code == 403:
                print(f"IP Blocked (403) at page {page_number}.")
                break

            soup = BeautifulSoup(response.content, 'html.parser')
            cards = soup.find_all('div', class_='mb-srp__card')
            
            if not cards:
                print(f"No listings found on page {page_number}. Ending.")
                break

            for card in cards:
                try:
                    # 1. Listing URL 
                    link_tag = card.find('a', class_='mb-srp__card__link') or \
                               card.find('a', class_='mb-srp__card--title') or \
                               card.find('a', href=True)
                    
                    listing_url = ""
                    if link_tag and 'href' in link_tag.attrs:
                        listing_url = link_tag['href']
                        if not listing_url.startswith('http'):
                            listing_url = 'https://www.magicbricks.com' + listing_url

                    # 2. Locality - Targeting specific location span or secondary title
                    loc_tag = card.find('span', class_='mb-srp__card--location') or \
                              card.find('div', class_='mb-srp__card__location')
                    
                    full_location = loc_tag.text.strip() if loc_tag else ""
                    
                    # If location tag is empty
                    if not full_location:
                        title_tag = card.find(['h2', 'span'], class_='mb-srp__card--title')
                        if title_tag and " in " in title_tag.text:
                            full_location = title_tag.text.split(" in ")[-1]
                    
                    # Clean locality: Take the first part before comma, uppercase
                    locality = full_location.split(',')[0].strip().upper() if full_location else "UNKNOWN"
                    if locality == "NAGPUR" or not locality: locality = "UNKNOWN"

                    # 3. Property Type - Deduction from title
                    title_tag = card.find(['h2', 'span'], class_='mb-srp__card--title')
                    title_text = title_tag.text.strip().lower() if title_tag else ""
                    
                    property_type = "Flat"
                    if "plot" in title_text: property_type = "Plot"
                    elif "house" in title_text: property_type = "House"
                    elif "villa" in title_text: property_type = "Villa"
                    elif "penthouse" in title_text: property_type = "Penthouse"

                    # 4. Total Price (Numeric)
                    price_raw = card.find('div', class_='mb-srp__card__price--amount')
                    total_price = clean_numeric_value(price_raw.text) if price_raw else 0

                    # 5. Area Sqft (Numeric) - More robust selectors for area
                    # Magicbricks often puts this in a div with data-summary or a summary value class
                    area_tag = card.find('div', {'data-summary': 'displayUnit'}) or \
                               card.find('div', class_='mb-srp__card__summary--value') or \
                               card.find('div', class_='mb-srp__card__area')
                    
                    area_sqft = clean_numeric_value(area_tag.text) if area_tag else 0

                    # 6. Price per Sqft (Numeric)
                    pps_tag = card.find('div', class_='mb-srp__card__price--size') or \
                              card.find('div', class_='mb-srp__card__pps')
                    
                    price_per_sqft = clean_numeric_value(pps_tag.text) if pps_tag else 0

                    # Only append if we have meaningful data
                    if locality != "UNKNOWN" and listing_url:
                        all_data.append({
                            'locality': locality,
                            'property_type': property_type,
                            'total_price': total_price,
                            'area_sqft': area_sqft,
                            'price_per_sqft': price_per_sqft,
                            'scrape_date': scrape_date,
                            'listing_url': listing_url
                        })
                    
                    if len(all_data) >= target_count: break
                    
                except Exception:
                    continue

            print(f"Page {page_number}: Collected {len(all_data)} items.")
            page_number += 1
            time.sleep(random.uniform(10, 15))

        except Exception as e:
            print(f"Error at page {page_number}: {e}")
            break

    # Final Save
    if all_data:
        df = pd.DataFrame(all_data)
        filename = "nagpur_real_estate_raw.csv" 
        save_path = os.path.join(output_folder, filename)
        df.to_csv(save_path, index=False)
        print(f"\nScraping Complete. Final Count: {len(df)} listings.")
        print(f"CSV saved to: {save_path}")
        print("\nDataset Preview:")
        print(df.head())
        return df
    else:
        print("No data collected. Verify if Magicbricks updated its selectors.")
        return None

if __name__ == "__main__":
    scrape_nagpur_magicbricks(target_count=300)


# In[8]:


from IPython.display import FileLink
FileLink("./Real_estate_Nagpur_MB/Data/Nagpur/Flats/nagpur_real_estate_raw.csv")


# In[ ]:




