import requests
import json

# Test against local server
url = "http://127.0.0.1:5000/quiz"

payload = {
    "email": "22f1001439@ds.study.iitm.ac.in",
    "secret": "iitm",
    "url": "https://tds-llm-analysis.s-anand.net/demo"
}

try:
    resp = requests.post(url, json=payload)
    print(f"Status Code: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")