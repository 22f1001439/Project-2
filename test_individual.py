from quiz_solver import solve_scrape_secret, solve_csv_question

print("=" * 50)
print("TESTING SCRAPE FUNCTION")
print("=" * 50)

# Test scrape function
scrape_url = "https://tds-llm-analysis.s-anand.net/demo-scrape?email=22f1001439%40ds.study.iitm.ac.in&id=5524"
scrape_instructions = {
    "question": "Scrape /demo-scrape-data?email=22f1001439@ds.study.iitm.ac.in (relative to this page). Get the secret code from this page. POST the secret code back to /submit",
    "submit_url": "https://tds-llm-analysis.s-anand.net/submit",
    "data_url": "",
    "answer_format": "string"
}

scrape_result = solve_scrape_secret(scrape_url, scrape_instructions)
print(f"SCRAPE RESULT: {scrape_result}")

print("\n" + "=" * 50)
print("TESTING CSV FUNCTION")
print("=" * 50)

# Test CSV function
csv_url = "https://tds-llm-analysis.s-anand.net/demo-audio?email=22f1001439%40ds.study.iitm.ac.in&id=5525"
csv_page_text = "CSV file\nCutoff: 28040\nPOST to JSON to https://tds-llm-analysis.s-anand.net/submit"
csv_instructions = {
    "question": "CSV file\nCutoff: 28040\nPOST to JSON to https://tds-llm-analysis.s-anand.net/submit",
    "submit_url": "https://tds-llm-analysis.s-anand.net/submit", 
    "data_url": "",
    "answer_format": "number"
}

csv_result = solve_csv_question(csv_url, csv_page_text, csv_instructions)
print(f"CSV RESULT: {csv_result}")