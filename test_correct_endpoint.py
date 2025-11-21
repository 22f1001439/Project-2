import requests
import json
import time

base_url = "https://project-2.onrender.com"

print("Testing the correct quiz solver endpoints...")

# Test health endpoint
try:
    health_url = f"{base_url}/health"
    response = requests.get(health_url, timeout=30)
    print(f"Health check - Status: {response.status_code}")
    print(f"Health response: {response.json()}")
except Exception as e:
    print(f"Health check failed: {e}")

print("\nTesting the quiz solving endpoint...")

# Test the correct endpoint with proper payload
try:
    quiz_url = f"{base_url}/quiz"
    
    # Prepare the request payload
    payload = {
        "email": "test@example.com",
        "secret": "iitm",
        "url": "https://aipe-masti.streamlit.app/"
    }
    
    print(f"Posting to: {quiz_url}")
    print(f"Payload: {payload}")
    
    start_time = time.time()
    response = requests.post(
        quiz_url,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=300  # 5 minutes
    )
    end_time = time.time()
    
    print(f"\nResponse time: {end_time - start_time:.2f} seconds")
    print(f"Status code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("\n=== SUCCESS! Quiz Results ===")
        for key, value in data.items():
            if key == "results":
                print(f"{key}:")
                for result_key, result_value in value.items():
                    print(f"  {result_key}: {result_value}")
            else:
                print(f"{key}: {value}")
    else:
        try:
            error_data = response.json()
            print(f"Error response: {error_data}")
        except:
            print(f"Error response: {response.text}")
            
except Exception as e:
    print(f"Request failed: {e}")