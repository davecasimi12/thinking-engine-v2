from playwright.sync_api import sync_playwright

# Nivora Bubble editor bot - Test 1 (just open the editor)
def open_nivora_editor():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # show the browser window
        page = browser.new_page()

        # 🔹 Replace this string with your actual Bubble editor URL
        bubble_editor_url = "https://bubble.io/page?id=nova-promo-88153&tab=Design&name=index"

        # Go to your Nivora editor
        page.goto(bubble_editor_url, wait_until="domcontentloaded")

        # Wait so you can log in / look around manually (30 seconds)
        page.wait_for_timeout(999999999)

        browser.close()


if __name__ == "__main__":
    open_nivora_editor()