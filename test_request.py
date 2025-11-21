import requests
import json

url = "http://127.0.0.1:5000/quiz"

payload = {
    "email": "22f1001439@ds.study.iitm.ac.in",
    "secret": "iitm",  
    "url": "https://tds-llm-analysis.s-anand.net/demo"
}

resp = requests.post(url, json=payload)
print("Status:", resp.status_code)
print("Response JSON:", json.dumps(resp.json(), indent=2))
