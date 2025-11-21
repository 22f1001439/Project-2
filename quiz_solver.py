from playwright.sync_api import sync_playwright


def fetch_page_text(url: str, wait_ms: int = 2000) -> str:
    """
    Open the given URL in a headless Chromium browser,
    wait for JavaScript to run, and return the page's body text.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Go to the quiz page and wait until network is mostly idle
        page.goto(url, wait_until="networkidle")

        # Small extra wait to let any JS (like atob(...) decoders) finish
        page.wait_for_timeout(wait_ms)

        # Get the visible text from the page
        text = page.inner_text("body")

        browser.close()

    return text
