from playwright.sync_api import sync_playwright

def simple_test():
    """Simple test to see which browser is being used"""
    try:
        with sync_playwright() as p:
            print(f"Available browsers: {list(p.__dict__.keys())}")
            browser = p.firefox.launch(headless=True)
            print("✅ Firefox launched successfully")
            page = browser.new_page()
            page.goto("https://httpbin.org/json")
            content = page.content()
            browser.close()
            return f"SUCCESS: Retrieved {len(content)} characters"
    except Exception as e:
        return f"ERROR: {e}"

if __name__ == "__main__":
    print("Testing Playwright browser availability...")
    result = simple_test()
    print(result)