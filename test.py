from playwright.sync_api import Playwright, sync_playwright


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://onehousing.vn/cong-cu/dinh-gia")

    page.locator(
        "xpath=/html/body/div[2]/div[4]/div[2]/div/div[2]/div/div[2]/div[1]/div[1]/form/div/div[1]"
    ).click()
    page.get_by_text("TP.Hà Nội").click()
    page.get_by_text("Nguyễn Tuân").click()
    page.get_by_text("HH1").click()

    input()

    # ---------------------
    context.close()
    browser.close()


def main():
    with sync_playwright() as playwright:
        run(playwright)


if __name__ == "__main__":
    main()
