import requests
import time

# Test health endpoint
url = "https://quizsolver-production-c89b.up.railway.app/health"

print("Testing health endpoint...")
try:
    response = requests.get(url, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")

print("\nTesting main quiz endpoint...")
# Test main endpoint
url = "https://quizsolver-production-c89b.up.railway.app/solve_quiz"

try:
    response = requests.get(url, timeout=30)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        try:
            data = response.json()
            print("Response data:", data)
        except:
            print("Response text:", response.text[:500])
    else:
        print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")