import requests
import time

base_url = "https://project-2.onrender.com"

print(f"Testing main quiz endpoint directly...")

try:
    quiz_url = f"{base_url}/solve_quiz"
    print(f"Requesting: {quiz_url}")
    
    # Start timing
    start_time = time.time()
    response = requests.get(quiz_url, timeout=300)
    end_time = time.time()
    
    print(f"Response time: {end_time - start_time:.2f} seconds")
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        try:
            data = response.json()
            print("\n=== SUCCESS! Quiz Results ===")
            for key, value in data.items():
                print(f"{key}: {value}")
        except Exception as json_error:
            print(f"JSON parse error: {json_error}")
            print("Raw response:", response.text[:500])
    else:
        print("Error response:")
        print(response.text[:500])
        
except requests.exceptions.Timeout:
    print("Request timed out after 5 minutes")
except Exception as e:
    print(f"Error: {e}")