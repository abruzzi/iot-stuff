from tracker_core import run_tracker


RUN_CONFIG = {
    "version": "v2_p_control_no_smoothing",
    "controller_mode": "p",

    # V2: first control version, no smoothing
    "use_smoothing": False,
    "use_stable_detection": True,

    "camera_horizontal_fov": 90,
    "dead_zone": 7,
    "smoothing_alpha": 0.3,

    "direction": -1,

    "kp": 0.5,
    "kd": 0,
    "max_step_deg": 5,
    "send_interval": 0.1,

    "use_arduino": True,
    "serial_port": "/dev/cu.usbmodem21301",
    "serial_baud": 9600,

    "camera_index": 0,
    "min_detection_confidence": 0.6,
    "stable_window_size": 5,
    "stable_required_count": 3,
}


if __name__ == "__main__":
    run_tracker(RUN_CONFIG)
