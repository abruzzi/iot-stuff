import time
from playwright.sync_api import sync_playwright, Error


STATE_SCRIPT = """
() => {
  const runner = Runner.getInstance();

  return {
    crashed: runner.crashed,
    speed: runner.currentSpeed,
    trexX: runner.tRex.xPos,
    trexY: runner.tRex.yPos,
    jumping: runner.tRex.jumping,
    ducking: runner.tRex.ducking,
    obstacles: runner.horizon.obstacles.map(o => ({
      x: o.xPos,
      y: o.yPos,
      width: o.width,
      height: o.height ?? o.typeConfig?.height,
      type: o.typeConfig?.type
    }))
  };
}
"""


def should_jump(state):
    obstacles = state["obstacles"]

    if not obstacles:
        return False

    # Dino 正在跳的时候，不要重复触发跳跃
    if state.get("jumping"):
        return False

    obstacle = obstacles[0]

    distance = obstacle["x"] - state["trexX"]
    speed = state["speed"]
    obstacle_type = obstacle["type"]

    is_cactus = obstacle_type in [
        "cactusSmall",
        "cactusLarge",
        "CACTUS_SMALL",
        "CACTUS_LARGE",
    ]

    if not is_cactus:
        return False

    jump_distance = 45 + speed * 8

    return 0 < distance < jump_distance

with sync_playwright() as p:
    browser = p.chromium.launch(
        channel="chrome",
        headless=False,
    )

    page = browser.new_page()

    try:
        page.goto("chrome://dino")
    except Error as error:
        print("Navigation error is expected for chrome://dino, continuing...")

    # 等待 Dino 的 Runner 出现
    page.wait_for_function("() => typeof Runner !== 'undefined' && Runner.getInstance")

    # 开始游戏
    page.keyboard.press("Space")

    while True:
        try:
            state = page.evaluate(STATE_SCRIPT)
        except Exception as error:
            print("Failed to read state:", error)
            time.sleep(0.1)
            continue

        if state["crashed"]:
            print("Game over. Restarting...")
            page.keyboard.press("Space")
            time.sleep(0.5)
            continue

        if should_jump(state):
            page.keyboard.press("Space")

        time.sleep(0.005)