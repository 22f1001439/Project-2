import requests
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright
import re

# Let's manually inspect what's on the scraping page with Playwright
base_url = "https://tds-llm-analysis.s-anand.net/demo-scrape?email=22f1001439%40ds.study.iitm.ac.in&id=5505"

print("1. Using Playwright to get rendered page content:")
with sync_playwright() as p:
    browser = p.firefox.launch(headless=True)
    page = browser.new_page()
    page.goto(base_url, wait_until="networkidle")
    page.wait_for_timeout(2000)
    rendered_text = page.inner_text("body")
    browser.close()

print(f"Rendered content:\n{rendered_text}")

print("\n" + "="*50)

# Extract the demo-scrape-data URL from rendered content
m = re.search(r'/demo-scrape-data[^\s"<>)]*', rendered_text)
if m:
    rel_path = m.group(0)
    scrape_data_url = urljoin(base_url, rel_path)
    print(f"2. Found scrape data URL: {scrape_data_url}")
    
    # Now get the data from that URL using Playwright too
    print("3. Using Playwright to get scrape data content:")
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()
        page.goto(scrape_data_url, wait_until="networkidle")
        page.wait_for_timeout(2000)
        data_content = page.inner_text("body")
        browser.close()
    
    print(f"Scraped data content: '{data_content}'")
    
    # Look for secret patterns in the scraped content
    patterns = [
        r'[Ss]ecret[^:]*:\s*([A-Za-z0-9_\-]{6,})',
        r'"secret":\s*"([^"]+)"',
        r"'secret':\s*'([^']+)'",
        r'secret[^:]*:\s*([A-Za-z0-9_\-]{6,})',
        r'([A-Za-z0-9_\-]{8,})',  # Any long token
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, data_content, re.IGNORECASE)
        if matches:
            print(f"Pattern '{pattern}' found: {matches}")
            # Filter out common words
            filtered = [m for m in matches if m.lower() not in ['question', 'response', 'document', 'function']]
            if filtered:
                print(f"Filtered matches: {filtered}")
                print(f"POTENTIAL SECRET: {filtered[0]}")
        
else:
    print("Could not find demo-scrape-data URL in rendered content")