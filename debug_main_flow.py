from quiz_solver import fetch_page_text, extract_instructions_from_page

print("=" * 60)
print("DEBUG: Testing page text extraction")
print("=" * 60)

# Test the scrape page
scrape_url = "https://tds-llm-analysis.s-anand.net/demo-scrape?email=22f1001439%40ds.study.iitm.ac.in&id=5524"
print(f"1. Testing scrape URL: {scrape_url}")

page_text = fetch_page_text(scrape_url)
print(f"Page text length: {len(page_text)}")
print(f"Page text content:\n{page_text}")

instructions = extract_instructions_from_page(page_text)
print(f"Instructions: {instructions}")

# Check what the decision logic would be
q_lower = instructions["question"].lower()
print(f"Question lower: {q_lower}")
print(f"Contains 'demo-scrape-data': {'demo-scrape-data' in instructions['question']}")
print(f"Contains 'secret code': {'secret code' in q_lower}")

print("\n" + "=" * 60)

# Test the CSV page
csv_url = "https://tds-llm-analysis.s-anand.net/demo-audio?email=22f1001439%40ds.study.iitm.ac.in&id=5525"
print(f"2. Testing CSV URL: {csv_url}")

page_text2 = fetch_page_text(csv_url)
print(f"Page text length: {len(page_text2)}")
print(f"Page text content:\n{page_text2}")

instructions2 = extract_instructions_from_page(page_text2)
print(f"Instructions: {instructions2}")

# Check what the decision logic would be
q_lower2 = instructions2["question"].lower()
print(f"Question lower: {q_lower2}")
print(f"Contains 'csv file': {'csv file' in q_lower2}")
print(f"Contains '.csv': {'.csv' in q_lower2}")
print(f"data_url ends with .csv: {instructions2['data_url'].endswith('.csv') if instructions2['data_url'] else False}")