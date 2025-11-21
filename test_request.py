import requests
import json

url = "https://tds-quiz-bot.onrender.com/quiz"

payload = {
    "email": "22f1001439@ds.study.iitm.ac.in",
    "secret": "iitm",
    "url": "https://tds-llm-analysis.s-anand.net/demo"
}

resp = requests.post(url, json=payload)
print(resp.status_code)
print(json.dumps(resp.json(), indent=2))
