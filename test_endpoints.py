import requests

base_url = "https://project-2.onrender.com"

print("Testing root endpoint...")

try:
    response = requests.get(base_url, timeout=30)
    print(f"Status code: {response.status_code}")
    print("Response:")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")

# Try common endpoint variations
endpoints_to_try = [
    "/",
    "/quiz", 
    "/solve",
    "/api/solve_quiz",
    "/health"
]

for endpoint in endpoints_to_try:
    try:
        url = base_url + endpoint
        response = requests.get(url, timeout=10)
        print(f"\n{endpoint}: Status {response.status_code}")
        if response.status_code == 200:
            print(f"Content: {response.text[:200]}")
    except:
        print(f"\n{endpoint}: Error")