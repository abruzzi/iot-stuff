from tracker_core import run_tracker


RUN_CONFIG = {
    "version": "v0_detection_only",
    "controller_mode": "none",

    # V0: observe raw signal only
    "use_smoothing": False,
    "use_stable_detection": True,

    "camera_horizontal_fov": 90,
    "dead_zone": 7,
    "smoothing_alpha": 0.3,

    "direction": -1,

    # Not used in V0, but saved into metadata for consistency
    "kp": 0,
    "kd": 0,
    "max_step_deg": 0,
    "send_interval": 0.1,

    # V0 does not need Arduino. Set to True only if you want to log servo feedback.
    "use_arduino": False,
    "serial_port": "/dev/cu.usbmodem21201",
    "serial_baud": 9600,

    "camera_index": 0,
    "min_detection_confidence": 0.6,
    "stable_window_size": 5,
    "stable_required_count": 3,
}


if __name__ == "__main__":
    run_tracker(RUN_CONFIG)
