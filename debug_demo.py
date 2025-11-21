import requests
from quiz_solver import fetch_page_text, extract_instructions_from_page

def debug_demo_page():
    """Debug the demo page content and instruction extraction"""
    url = "https://tds-llm-analysis.s-anand.net/demo"
    
    print("🔍 Fetching demo page...")
    page_text = fetch_page_text(url)
    
    print(f"📄 Page content ({len(page_text)} chars):")
    print("=" * 60)
    print(page_text[:2000])  # First 2000 chars
    print("=" * 60)
    
    print("\n🧠 Extracting instructions...")
    instructions = extract_instructions_from_page(page_text)
    
    print(f"📋 Extracted instructions:")
    for key, value in instructions.items():
        print(f"  {key}: '{value}'")

if __name__ == "__main__":
    debug_demo_page()