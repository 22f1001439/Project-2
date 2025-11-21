import requests
import json

url = "https://project-2-st54.onrender.com/quiz"


payload = {
    "email": "22f1001439@ds.study.iitm.ac.in",
    "secret": "iitm",
    "url": "https://tds-llm-analysis.s-anand.net/demo"
}

resp = requests.post(url, json=payload)
print(resp.status_code)

try:
    print(json.dumps(resp.json(), indent=2))
except json.JSONDecodeError:
    print("Response is not JSON:")
    print(resp.text)
