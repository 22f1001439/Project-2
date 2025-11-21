import requests
import json
import time

def test_quiz_solver():
    """Test the quiz solver with the demo endpoint"""
    
    # Test locally first
    local_url = "http://127.0.0.1:5000/quiz"
    remote_url = "https://project-2-owij.onrender.com/quiz"
    
    payload = {
        "email": "22f1001439@ds.study.iitm.ac.in",
        "secret": "iitm", 
        "url": "https://tds-llm-analysis.s-anand.net/demo"
    }
    
    print("🧪 Testing Quiz Solver API...")
    print("=" * 50)
    
    # Try local first, then remote
    for name, url in [("Local", local_url), ("Remote", remote_url)]:
        print(f"\n📡 Testing {name} endpoint: {url}")
        
        try:
            start_time = time.time()
            response = requests.post(url, json=payload, timeout=60)
            end_time = time.time()
            
            print(f"⏱️  Response time: {end_time - start_time:.2f}s")
            print(f"📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ SUCCESS!")
                print(f"📧 Email: {data.get('email')}")
                print(f"🔗 URL: {data.get('url')}")
                print(f"📈 Status: {data.get('status')}")
                print(f"⚡ Processing time: {data.get('processing_time', 0):.2f}s")
                
                results = data.get('results', {})
                if results:
                    print(f"🔄 Total iterations: {results.get('total_iterations', 0)}")
                    print(f"🏁 Final status: {results.get('status', 'unknown')}")
                    
                    # Show each iteration briefly
                    for i, result in enumerate(results.get('results', [])[:3):  # Show first 3
                        print(f"  📝 Iteration {i+1}: Answer = {result.get('answer')}")
            else:
                print(f"❌ FAILED!")
                try:
                    error_data = response.json()
                    print(f"🔥 Error: {error_data.get('error', 'Unknown error')}")
                    print(f"📋 Details: {error_data.get('details', 'No details')}")
                except:
                    print(f"📋 Response: {response.text}")
                    
        except requests.exceptions.ConnectionError:
            print(f"🔌 Connection failed - {name} server not running")
        except requests.exceptions.Timeout:
            print(f"⏰ Request timeout - {name} server too slow")
        except Exception as e:
            print(f"💥 Error: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Test completed!")

if __name__ == "__main__":
    test_quiz_solver()