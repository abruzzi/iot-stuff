from playwright.sync_api import sync_playwright, Error


class DinoController:
    def __init__(self, page):
        self.page = page
        self.is_ducking = False

    def jump(self):
        self.page.keyboard.press("Space")

    def start_duck(self):
        if not self.is_ducking:
            self.page.keyboard.down("ArrowDown")
            self.is_ducking = True

    def stop_duck(self):
        if self.is_ducking:
            self.page.keyboard.up("ArrowDown")
            self.is_ducking = False

    def reset(self):
        self.stop_duck()
        self.page.keyboard.press("Space")


def open_dino():
    playwright = sync_playwright().start()

    browser = playwright.chromium.launch(
        channel="chrome",
        headless=False,
    )

    page = browser.new_page()

    try:
        page.goto("chrome://dino")
    except Error:
        print("Navigation error is expected for chrome://dino, continuing...")

    page.wait_for_function(
        "() => typeof Runner !== 'undefined' && typeof Runner.getInstance === 'function'"
    )

    controller = DinoController(page)

    # Start the game
    controller.jump()

    return playwright, browser, page, controller