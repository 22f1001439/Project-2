from playwright.sync_api import sync_playwright
import requests
from urllib.parse import urljoin
import re

# Let's debug the CSV question
audio_url = "https://tds-llm-analysis.s-anand.net/demo-audio?email=22f1001439%40ds.study.iitm.ac.in&id=5508"

print("1. Getting audio page content with Playwright:")
with sync_playwright() as p:
    browser = p.firefox.launch(headless=True)
    page = browser.new_page()
    page.goto(audio_url, wait_until="networkidle")
    page.wait_for_timeout(2000)
    audio_content = page.inner_text("body")
    browser.close()

print(f"Audio page content:\n{audio_content}")

print("\n" + "="*50)

# Look for CSV URL patterns
csv_patterns = [
    r'https?://[^\s"]+\.csv',
    r'https?://[^\s"]+(?=\s*CSV|csv)',
    r'(https?://[^\s"]+)\s*CSV',
    r'/[^\s"]*\.csv',
]

csv_url = None
for pattern in csv_patterns:
    matches = re.findall(pattern, audio_content, re.IGNORECASE)
    if matches:
        print(f"CSV pattern '{pattern}' found: {matches}")
        csv_url = matches[0]
        if isinstance(csv_url, tuple):
            csv_url = csv_url[0]
        if not csv_url.startswith('http'):
            csv_url = urljoin(audio_url, csv_url)
        if not csv_url.endswith('.csv'):
            csv_url += '.csv'
        break

if csv_url:
    print(f"2. Found CSV URL: {csv_url}")
    
    # Download CSV
    try:
        resp = requests.get(csv_url, timeout=30)
        print(f"CSV status: {resp.status_code}")
        print(f"CSV content preview:\n{resp.text[:500]}")
        
        # Parse CSV
        lines = resp.text.strip().splitlines()
        print(f"CSV has {len(lines)} lines")
        
        if lines:
            import csv
            reader = csv.reader(lines)
            rows = list(reader)
            header = rows[0] if rows else []
            data_rows = rows[1:] if len(rows) > 1 else []
            
            print(f"Header: {header}")
            print(f"Data rows: {len(data_rows)}")
            print(f"First few data rows: {data_rows[:3]}")
            
            # Look for cutoff value in audio page
            cutoff_match = re.search(r'Cutoff:\s*([0-9]+)', audio_content)
            if cutoff_match:
                cutoff = int(cutoff_match.group(1))
                print(f"Found cutoff: {cutoff}")
                
                # Try to find numeric columns
                for idx, col_name in enumerate(header):
                    values = []
                    for row in data_rows:
                        if idx < len(row):
                            try:
                                val = float(row[idx].replace(',', ''))
                                values.append(val)
                            except:
                                break
                    if values:
                        filtered_values = [v for v in values if v > cutoff]
                        total = sum(filtered_values)
                        print(f"Column '{col_name}': {len(values)} values, {len(filtered_values)} > {cutoff}, sum = {total}")
            
    except Exception as e:
        print(f"Error processing CSV: {e}")
else:
    print("No CSV URL found")