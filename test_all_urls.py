import requests
import time

# Common deployment platforms and possible URLs
possible_urls = [
    "https://quizsolver-production-c89b.up.railway.app",
    "https://project-2.onrender.com", 
    "https://project-2-git-main-22f1001439.vercel.app",
    "https://22f1001439-project-2.onrender.com",
    "https://quiz-solver.onrender.com"
]

for base_url in possible_urls:
    print(f"\n=== Testing {base_url} ===")
    
    # Test health endpoint
    try:
        health_url = f"{base_url}/health"
        response = requests.get(health_url, timeout=10)
        print(f"Health endpoint - Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Health response: {response.text}")
            
            # If health works, test main endpoint
            quiz_url = f"{base_url}/solve_quiz"
            quiz_response = requests.get(quiz_url, timeout=60)
            print(f"Quiz endpoint - Status: {quiz_response.status_code}")
            if quiz_response.status_code == 200:
                try:
                    data = quiz_response.json()
                    print("SUCCESS! Quiz response:", data)
                    break
                except:
                    print("Quiz response text:", quiz_response.text[:200])
            else:
                print(f"Quiz error: {quiz_response.text[:200]}")
        else:
            print(f"Health error: {response.text[:100]}")
            
    except requests.exceptions.ConnectTimeout:
        print("Connection timeout")
    except requests.exceptions.ConnectionError:
        print("Connection error - service not found")
    except Exception as e:
        print(f"Error: {e}")