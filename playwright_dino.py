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

OVERLAY_SCRIPT = """
() => {
  if (window.__dinoDebugOverlayInstalled) {
    return;
  }

  window.__dinoDebugOverlayInstalled = true;

  const gameCanvas = document.querySelector('.runner-canvas');

  if (!gameCanvas) {
    console.warn('Dino canvas not found');
    return;
  }

  const wrapper = document.createElement('div');
  wrapper.id = 'dino-debug-overlay';

  wrapper.style.position = 'fixed';
  wrapper.style.pointerEvents = 'none';
  wrapper.style.zIndex = '9999';
  wrapper.style.fontFamily = 'monospace';
  wrapper.style.fontSize = '12px';
  wrapper.style.color = 'red';

  document.body.appendChild(wrapper);

  function syncOverlayPosition() {
    const rect = gameCanvas.getBoundingClientRect();

    wrapper.style.left = rect.left + 'px';
    wrapper.style.top = rect.top + 'px';
    wrapper.style.width = rect.width + 'px';
    wrapper.style.height = rect.height + 'px';

    return rect;
  }

  function createBox(x, y, w, h, label, rect, color) {
    const box = document.createElement('div');

    const scaleX = rect.width / gameCanvas.width;
    const scaleY = rect.height / gameCanvas.height;

    box.style.position = 'absolute';
    box.style.left = (x * scaleX) + 'px';
    box.style.top = (y * scaleY) + 'px';
    box.style.width = (w * scaleX) + 'px';
    box.style.height = (h * scaleY) + 'px';
    box.style.border = `2px solid ${color}`;
    box.style.boxSizing = 'border-box';

    const text = document.createElement('div');
    text.textContent = label;

    text.style.position = 'absolute';
    text.style.left = '0px';
    text.style.top = '-18px';
    text.style.whiteSpace = 'nowrap';
    text.style.color = `${color}`;
    text.style.background = 'rgba(255, 255, 255, 0.75)';
    text.style.padding = '1px 3px';
    text.style.borderRadius = '3px';

    box.appendChild(text);

    wrapper.appendChild(box);
  }

  function draw() {
    const runner = Runner.getInstance();

    const rect = syncOverlayPosition();

    wrapper.innerHTML = '';

    if (!runner) {
      requestAnimationFrame(draw);
      return;
    }

    const trex = runner.tRex;

    const trexWidth = trex.ducking ? 59 : 44;
    const trexHeight = trex.ducking ? 25 : 47;

    createBox(
      trex.xPos,
      trex.yPos,
      trexWidth,
      trexHeight,
      `trex y=${Math.round(trex.yPos)}`,
      rect,
      'green'
    );

    for (const obstacle of runner.horizon.obstacles) {
      const type = obstacle.typeConfig?.type ?? 'obstacle';
      const width = obstacle.width;
      const height = obstacle.height ?? obstacle.typeConfig?.height ?? 40;

      createBox(
        obstacle.xPos,
        obstacle.yPos,
        width,
        height,
        `${type} w=${Math.round(width)}`,
        rect,
        'red'
      );
    }

    requestAnimationFrame(draw);
  }

  draw();
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

    if width < 30:
        return 0.10

    if width < 60:
        return 0.22

    if width < 90:
        return 0.32

    return 0.36


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
        if width < 30:
            jump_distance = 45 + speed * 8
        elif width < 60:
            jump_distance = 48 + speed * 8
        elif width < 90:
            # 大仙人掌组：不要太早跳，主要靠更长按住 Space
            jump_distance = 50 + speed * 8
        else:
            jump_distance = 55 + speed * 8

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

    page.wait_for_function("() => typeof Runner !== 'undefined' && Runner.getInstance")

    page.keyboard.press("Space")

    page.wait_for_function("""
    () => {
    const runner = Runner.getInstance();
    return runner && runner.playing;
    }
    """)

    time.sleep(0.3)

    # 开始游戏
    page.evaluate(OVERLAY_SCRIPT)

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