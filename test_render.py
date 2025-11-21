import requests
import time

# Test the most likely URL with longer timeout
base_url = "https://project-2.onrender.com"

print(f"Testing {base_url} with extended timeout...")

try:
    # Test health endpoint with longer timeout
    health_url = f"{base_url}/health"
    print("Trying health endpoint...")
    response = requests.get(health_url, timeout=120)  # 2 minute timeout
    print(f"Health endpoint - Status: {response.status_code}")
    print(f"Health response: {response.text}")
    
    if response.status_code == 200:
        print("\nHealth check passed! Testing quiz endpoint...")
        # Test main endpoint
        quiz_url = f"{base_url}/solve_quiz"
        quiz_response = requests.get(quiz_url, timeout=300)  # 5 minute timeout
        print(f"Quiz endpoint - Status: {quiz_response.status_code}")
        
        if quiz_response.status_code == 200:
            try:
                data = quiz_response.json()
                print("SUCCESS! Quiz response:")
                for key, value in data.items():
                    print(f"  {key}: {value}")
            except:
                print("Quiz response text:", quiz_response.text)
        else:
            print(f"Quiz error: {quiz_response.text}")
    else:
        print("Health check failed")
        
except requests.exceptions.Timeout:
    print("Request timed out - service might be cold starting")
except Exception as e:
    print(f"Error: {e}")