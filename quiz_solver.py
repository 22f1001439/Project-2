from playwright.sync_api import sync_playwright

def fetch_page_text(url: str, wait_ms: int = 2000) -> str:
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)  # ← FIXED
        page = browser.new_page()

        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(wait_ms)

        text = page.inner_text("body")

        browser.close()

    return text
