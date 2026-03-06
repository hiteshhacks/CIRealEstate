import requests
import json

BASE = "http://localhost:8000"

# 1. Get localities
r = requests.get(f"{BASE}/localities")
data = r.json()
locs = data["localities"]
print(f"Total localities: {len(locs)}")
print(f"Data date: {data['data_date']}")
print(f"First 5: {locs[:5]}")
print()

# 2. Summary for first locality
loc = locs[0]
r2 = requests.get(f"{BASE}/locality/{loc}/summary")
print(f"--- Summary for {loc} ---")
print(json.dumps(r2.json(), indent=2))
print()

# 3. Prices
r3 = requests.get(f"{BASE}/locality/{loc}/prices")
d = r3.json()
print(f"--- Prices for {loc} ---")
print(f"Count: {len(d['prices'])}, Sample: {d['prices'][:3]}")
print()

# 4. Top/bottom
r4 = requests.get(f"{BASE}/top_localities")
t = r4.json()
print("--- Top 5 Expensive ---")
for x in t["top5"]:
    print(f"  {x['locality']}: {x['avg_price_per_sqft']}")
print("--- Top 5 Affordable ---")
for x in t["bottom5"]:
    print(f"  {x['locality']}: {x['avg_price_per_sqft']}")
print()

# 5. Compare
if len(locs) >= 2:
    pair = f"{locs[0]},{locs[1]}"
    r5 = requests.get(f"{BASE}/compare", params={"localities": pair})
    print(f"--- Compare {pair} ---")
    print(json.dumps(r5.json(), indent=2))
    print()

# 6. Scrape status
r6 = requests.get(f"{BASE}/scrape/status")
print("--- Scrape Status ---")
print(json.dumps(r6.json(), indent=2))
