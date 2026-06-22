from playwright.sync_api import sync_playwright, Error


GAME_STATE_SCRIPT = """
() => {
  const runner = Runner.getInstance();

  const obstacle = runner.horizon.obstacles[0];

  return {
    crashed: runner.crashed,
    speed: runner.currentSpeed,
    trexX: runner.tRex.xPos,
    trexY: runner.tRex.yPos,
    jumping: runner.tRex.jumping,
    ducking: runner.tRex.ducking,
    obstacle: obstacle ? {
      x: obstacle.xPos,
      y: obstacle.yPos,
      width: obstacle.width,
      height: obstacle.height ?? obstacle.typeConfig?.height,
      type: obstacle.typeConfig?.type,
      distance: obstacle.xPos - (runner.tRex.xPos + 44)
    } : null
  };
}
"""

class DinoController:
    def __init__(self, page):
        self.page = page
        self.is_ducking = False

    def read_state(self):
        return self.page.evaluate(GAME_STATE_SCRIPT)

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

    def is_crashed(self):
        state = self.read_state()
        return state["crashed"], state


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