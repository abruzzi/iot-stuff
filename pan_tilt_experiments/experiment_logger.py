import csv
import json
import os
import time
from datetime import datetime


class ExperimentLogger:
    def __init__(self, config, log_dir="logs"):
        self.config = config
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)

        self.run_id = config.get("run_id") or self._build_run_id(config)
        self.start_time = time.perf_counter()

        self.csv_path = os.path.join(self.log_dir, f"{self.run_id}.csv")
        self.meta_path = os.path.join(self.log_dir, f"{self.run_id}_meta.json")

        self.csv_file = open(self.csv_path, "w", newline="")
        self.csv_writer = csv.DictWriter(self.csv_file, fieldnames=self._fieldnames())
        self.csv_writer.writeheader()

        self._write_metadata()

    def _build_run_id(self, config):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        version = config.get("version", "experiment")
        return f"{timestamp}_{version}"

    def _fieldnames(self):
        return [
            "run_id",
            "timestamp",
            "elapsed_s",
            "frame_index",

            "event",

            # Face detection state
            "face_detected",
            "stable_face_detected",
            "recent_detection_count",

            # Frame info
            "frame_width",
            "frame_height",
            "frame_center_x",
            "frame_center_y",

            # Bounding box
            "bbox_x",
            "bbox_y",
            "bbox_w",
            "bbox_h",

            # Face center
            "raw_face_center_x",
            "raw_face_center_y",
            "smoothed_face_center_x",
            "smoothed_face_center_y",

            # Error calculation
            "horizontal_distance",
            "vertical_distance",
            "angle_error",
            "normalized_error",
            "within_dead_zone",

            # Controller config
            "version",
            "controller_mode",
            "use_smoothing",
            "use_stable_detection",
            "fixed_step_deg",
            "kp",
            "kd",
            "max_step_deg",
            "send_interval",
            "dead_zone",
            "smoothing_alpha",

            # Control output
            "p_term",
            "d_term",
            "error_velocity",
            "pan_delta",
            "tilt_delta",
            "command",
            "command_sent",
            "send_skipped_reason",
            "time_since_last_send_s",

            # Arduino feedback
            "arduino_line",
            "servo_angle",
            "servo_previous_angle",
            "servo_delta",

            # Extra notes
            "note",
        ]

    def _write_metadata(self):
        metadata = {
            **self.config,
            "run_id": self.run_id,
            "started_at": datetime.now().isoformat(),
            "csv_path": self.csv_path,
            "meta_path": self.meta_path,
        }

        with open(self.meta_path, "w") as f:
            json.dump(metadata, f, indent=2)

    def elapsed(self):
        return time.perf_counter() - self.start_time

    def log(self, frame_index, event="", **kwargs):
        row = self._base_row(frame_index, event)
        row.update(kwargs)

        allowed_fields = set(self._fieldnames())
        row = {key: value for key, value in row.items() if key in allowed_fields}

        self.csv_writer.writerow(row)
        self.csv_file.flush()

    def _base_row(self, frame_index, event):
        return {
            "run_id": self.run_id,
            "timestamp": datetime.now().isoformat(),
            "elapsed_s": round(self.elapsed(), 6),
            "frame_index": frame_index,

            "event": event,

            "face_detected": "",
            "stable_face_detected": "",
            "recent_detection_count": "",

            "frame_width": "",
            "frame_height": "",
            "frame_center_x": "",
            "frame_center_y": "",

            "bbox_x": "",
            "bbox_y": "",
            "bbox_w": "",
            "bbox_h": "",

            "raw_face_center_x": "",
            "raw_face_center_y": "",
            "smoothed_face_center_x": "",
            "smoothed_face_center_y": "",

            "horizontal_distance": "",
            "vertical_distance": "",
            "angle_error": "",
            "normalized_error": "",
            "within_dead_zone": "",

            "version": self.config.get("version", ""),
            "controller_mode": self.config.get("controller_mode", ""),
            "use_smoothing": self.config.get("use_smoothing", ""),
            "use_stable_detection": self.config.get("use_stable_detection", ""),
            "fixed_step_deg": self.config.get("fixed_step_deg", ""),
            "kp": self.config.get("kp", ""),
            "kd": self.config.get("kd", ""),
            "max_step_deg": self.config.get("max_step_deg", ""),
            "send_interval": self.config.get("send_interval", ""),
            "dead_zone": self.config.get("dead_zone", ""),
            "smoothing_alpha": self.config.get("smoothing_alpha", ""),

            "p_term": "",
            "d_term": "",
            "error_velocity": "",
            "pan_delta": "",
            "tilt_delta": "",
            "command": "",
            "command_sent": "",
            "send_skipped_reason": "",
            "time_since_last_send_s": "",

            "arduino_line": "",
            "servo_angle": "",
            "servo_previous_angle": "",
            "servo_delta": "",

            "note": "",
        }

    def close(self):
        self.csv_file.close()

    def print_paths(self):
        print(f"Log saved to: {self.csv_path}")
        print(f"Metadata saved to: {self.meta_path}")
