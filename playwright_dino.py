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

def get_bird_action(obstacle):
    y = obstacle["y"]

    if y >= 90:
        return "jump"   # 低空鸟，跳过去

    if y >= 60:
        return "duck"   # 中间鸟，低头

    return "ignore"     # 高空鸟，不处理

def should_release_duck(state):
    obstacles = state["obstacles"]

    if not obstacles:
        return True

    obstacle = obstacles[0]
    obstacle_type = obstacle["type"]

    is_bird = obstacle_type in [
        "pterodactyl",
        "PTERODACTYL",
    ]

    # 如果当前最近的障碍物不是鸟，可以释放
    if not is_bird:
        return True

    obstacle_right = obstacle["x"] + obstacle["width"]
    trex_left = state["trexX"]

    # 加一点安全距离，避免刚好擦边
    safe_gap = 10

    return obstacle_right < trex_left - safe_gap

def should_duck(state):
    obstacles = state["obstacles"]

    if not obstacles:
        return False

    if state.get("jumping"):
        return False

    obstacle = obstacles[0]

    obstacle_type = obstacle["type"]
    speed = state["speed"]

    is_bird = obstacle_type in [
        "pterodactyl",
        "PTERODACTYL",
    ]

    if not is_bird:
        return False

    action = get_bird_action(obstacle)

    if action != "duck":
        return False

    trex_width = 44
    distance = obstacle["x"] - (state["trexX"] + trex_width)

    duck_distance = 55 + speed * 10

    return 0 < distance < duck_distance


def get_jump_hold_time(obstacle):
    width = obstacle["width"]

    # 单个小仙人掌
    if width < 30:
        return 0.10

    # 两三个仙人掌
    if width < 60:
        return 0.16

    # 很宽的连续仙人掌
    return 0.24


def start_jump(page, hold_time):
    page.keyboard.down("Space")
    return time.time() + hold_time


def should_jump(state):
    obstacles = state["obstacles"]

    if not obstacles:
        return None

    if state.get("jumping") or state.get("ducking"):
        return None

    obstacle = obstacles[0]

    speed = state["speed"]
    obstacle_type = obstacle["type"]
    width = obstacle["width"]

    trex_width = 44
    distance = obstacle["x"] - (state["trexX"] + trex_width)

    is_cactus = obstacle_type in [
        "cactusSmall",
        "cactusLarge",
        "CACTUS_SMALL",
        "CACTUS_LARGE",
    ]

    is_bird = obstacle_type in [
        "pterodactyl",
        "PTERODACTYL",
    ]

    if is_cactus:
        # 宽仙人掌需要稍微早一点跳
        width_bonus = max(0, width - 30) * 0.5
        jump_distance = 45 + speed * 8 + width_bonus

        if 0 < distance < jump_distance:
            return get_jump_hold_time(obstacle)

        return None

    if is_bird:
        action = get_bird_action(obstacle)

        if action != "jump":
            return None

        jump_distance = 55 + speed * 9

        if 0 < distance < jump_distance:
            return 0.16

        return None

    return None

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

    is_ducking = False
    jump_release_at = None

    while True:
        state = page.evaluate(STATE_SCRIPT)


        if jump_release_at and time.time() >= jump_release_at:
            page.keyboard.up("Space")
            jump_release_at = None

        if state["obstacles"]:
            obstacle = state["obstacles"][0]
            if obstacle["type"] in ["pterodactyl", "PTERODACTYL"]:
                print("bird:", obstacle)

        if state["crashed"]:
            print("Game over. Restarting...")

            if is_ducking:
                page.keyboard.up("ArrowDown")
                is_ducking = False

            if jump_release_at:
                page.keyboard.up("Space")
                jump_release_at = None

            page.keyboard.press("Space")
            time.sleep(0.5)
            continue

        if is_ducking:
            if should_release_duck(state):
                page.keyboard.up("ArrowDown")
                is_ducking = False
        else:
            if should_duck(state):
                page.keyboard.down("ArrowDown")
                is_ducking = True

        hold_time = should_jump(state)

        if not is_ducking and hold_time is not None and jump_release_at is None:
            jump_release_at = start_jump(page, hold_time)

        time.sleep(0.005)