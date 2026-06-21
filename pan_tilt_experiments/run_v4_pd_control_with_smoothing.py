from tracker_core import run_tracker


RUN_CONFIG = {
    "version": "v4_pd_control_with_smoothing",
    "controller_mode": "pd",

    # V4: PD control with smoothing
    "use_smoothing": True,
    "use_stable_detection": True,

    "camera_horizontal_fov": 90,
    "dead_zone": 7,
    "smoothing_alpha": 0.3,

    "direction": -1,

    "kp": 0.25,
    "kd": 0.003,
    "max_step_deg": 3,
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
