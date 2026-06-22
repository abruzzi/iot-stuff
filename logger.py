import time
import csv

WRITE_CSV = False
PRINT_LOG = True
DEBUG = True
START_TIME = time.perf_counter()

FIELDNAMES = [
    "time_ms",
    "source",
    "event",
    "reason",

    # camera side
    "game_state",
    "y",
    "baseline",
    "velocity",
    "cooldown",
    "crouch_for",
    "dt",

    # game side
    "speed",
    "obstacle_type",
    "distance",
    "jumping",
    "ducking",
]

log_file = open("dino_debug_log.csv", "w", newline="")

log_writer = csv.DictWriter(
    log_file,
    fieldnames=FIELDNAMES,
    extrasaction="ignore",
)

log_writer.writeheader()


def now_ms():
    return int((time.perf_counter() - START_TIME) * 1000)


def debug_log(source, event, **data):
    if not DEBUG:
        return

    row = {
        "time_ms": now_ms(),
        "source": source,
        "event": event,
        **data,
    }

    if WRITE_CSV:
        log_writer.writerow(row)
        log_file.flush()

    if PRINT_LOG:
        details = " ".join(f"{key}={value}" for key, value in data.items())
        print(f"[{row['time_ms']:>6}ms] [{source}] {event} {details}")

def close_logger():
    log_file.close()