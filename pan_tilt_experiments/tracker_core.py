import math
import time
from collections import deque

import cv2
import mediapipe as mp

try:
    import serial
except ImportError:
    serial = None

from experiment_logger import ExperimentLogger
from arduino_state import ArduinoState


DEFAULT_CONFIG = {
    "version": "default",
    "controller_mode": "none",  # "none", "fixed", "p", "pd"

    "use_smoothing": False,
    "use_stable_detection": True,

    "camera_horizontal_fov": 90,
    "dead_zone": 7,
    "smoothing_alpha": 0.3,

    "direction": -1,

    "fixed_step_deg": 5,

    "kp": 0.5,
    "kd": 0.03,
    "max_step_deg": 5,
    "send_interval": 0.1,

    "serial_port": "/dev/cu.usbmodem21201",
    "serial_baud": 9600,
    "use_arduino": True,

    "camera_index": 0,
    "min_detection_confidence": 0.6,
    "stable_window_size": 5,
    "stable_required_count": 3,
}


class PanTiltTracker:
    def __init__(self, config):
        self.config = {**DEFAULT_CONFIG, **config}

        self.logger = ExperimentLogger(self.config)
        self.arduino_state = ArduinoState()

        self.arduino = None
        self.face_detection = None

        self.recent_face_detections = deque(
            maxlen=self.config["stable_window_size"]
        )

        self.last_sent_time = 0
        self.frame_index = 0

        self.smoothed_face_x = None
        self.smoothed_face_y = None

        self.last_angle_error = None
        self.last_error_time = None

    # -----------------------------
    # Setup / teardown
    # -----------------------------

    def setup(self):
        self._setup_arduino()
        self._setup_mediapipe()

    def _setup_arduino(self):
        if not self.config["use_arduino"]:
            print("Arduino disabled for this run.")
            return

        if serial is None:
            raise RuntimeError(
                "pyserial is not installed. Install it with: pip install pyserial"
            )

        self.arduino = serial.Serial(
            self.config["serial_port"],
            self.config["serial_baud"],
            timeout=0.05,
        )

        time.sleep(2)
        self.arduino.reset_input_buffer()

        print("Arduino connected.")

    def _setup_mediapipe(self):
        mp_face_detection = mp.solutions.face_detection
        self.face_detection = mp_face_detection.FaceDetection(
            model_selection=0,
            min_detection_confidence=self.config["min_detection_confidence"],
        )

    def close(self):
        if self.face_detection is not None:
            self.face_detection.close()

        if self.arduino is not None:
            self.arduino.close()

        self.logger.close()
        self.logger.print_paths()

    # -----------------------------
    # Arduino helpers
    # -----------------------------

    def read_arduino_lines(self):
        if self.arduino is None:
            return []

        lines = []

        while self.arduino.in_waiting > 0:
            try:
                line = self.arduino.readline().decode(
                    "utf-8", errors="ignore"
                ).strip()

                if line:
                    self.arduino_state.parse_line(line)
                    lines.append(line)

            except Exception:
                pass

        return lines

    def send_command(self, command):
        if self.arduino is None:
            return {
                "sent": False,
                "reason": "arduino_disabled",
                "command": command,
                "time_since_last_send_s": "",
                "arduino_lines": [],
            }

        now = time.time()
        time_since_last_send = now - self.last_sent_time

        if time_since_last_send < self.config["send_interval"]:
            return {
                "sent": False,
                "reason": "send_interval",
                "command": command,
                "time_since_last_send_s": time_since_last_send,
                "arduino_lines": [],
            }

        self.arduino.write(f"{command}\n".encode("utf-8"))
        self.arduino.flush()

        self.last_sent_time = now

        # Give Arduino a short moment to respond.
        time.sleep(0.03)

        arduino_lines = self.read_arduino_lines()

        print("sent", command)
        for line in arduino_lines:
            print("arduino:", line)

        return {
            "sent": True,
            "reason": "",
            "command": command,
            "time_since_last_send_s": time_since_last_send,
            "arduino_lines": arduino_lines,
        }

    # -----------------------------
    # Detection / math helpers
    # -----------------------------

    def is_face_stably_detected(self):
        return (
            sum(self.recent_face_detections)
            >= self.config["stable_required_count"]
        )

    def calculate_pan_angle(self, horizontal_distance, frame_width):
        horizontal_fov_rad = math.radians(self.config["camera_horizontal_fov"])
        focal_length_px = frame_width / (2 * math.tan(horizontal_fov_rad / 2))

        angle_rad = math.atan(horizontal_distance / focal_length_px)
        angle_deg = math.degrees(angle_rad)

        return self.config["direction"] * angle_deg

    def calculate_normalized_error(self, horizontal_distance, frame_width):
        return horizontal_distance / (frame_width / 2)

    def calculate_pan_delta_fixed(self, angle_error):
        if angle_error == 0:
            pan_delta = 0
        elif angle_error > 0:
            pan_delta = self.config["fixed_step_deg"]
        else:
            pan_delta = -self.config["fixed_step_deg"]

        pan_delta = self._limit_delta(pan_delta)

        return {
            "pan_delta": pan_delta,
            "p_term": "",
            "d_term": "",
            "error_velocity": "",
        }

    def calculate_pan_delta_p(self, angle_error):
        p_term = self.config["kp"] * angle_error
        pan_delta = round(p_term)
        pan_delta = self._limit_delta(pan_delta)

        return {
            "pan_delta": pan_delta,
            "p_term": p_term,
            "d_term": 0,
            "error_velocity": "",
        }

    def calculate_pan_delta_pd(self, angle_error):
        now = time.time()

        if self.last_angle_error is None or self.last_error_time is None:
            error_velocity = 0
        else:
            dt = now - self.last_error_time
            if dt <= 0:
                error_velocity = 0
            else:
                error_velocity = (angle_error - self.last_angle_error) / dt

        p_term = self.config["kp"] * angle_error
        d_term = self.config["kd"] * error_velocity

        output = p_term + d_term
        pan_delta = round(output)
        pan_delta = self._limit_delta(pan_delta)

        self.last_angle_error = angle_error
        self.last_error_time = now

        return {
            "pan_delta": pan_delta,
            "p_term": p_term,
            "d_term": d_term,
            "error_velocity": error_velocity,
        }

    def reset_pd_controller(self):
        self.last_angle_error = None
        self.last_error_time = None

    def _limit_delta(self, pan_delta):
        max_step = self.config["max_step_deg"]
        return max(min(pan_delta, max_step), -max_step)

    def get_largest_detection(self, detections, frame_width, frame_height):
        def area(detection):
            bbox = detection.location_data.relative_bounding_box
            w = bbox.width * frame_width
            h = bbox.height * frame_height
            return w * h

        return max(detections, key=area)

    # -----------------------------
    # Logging helper
    # -----------------------------

    def log_common_frame_state(
        self,
        *,
        event,
        face_detected,
        stable_face_detected,
        recent_detection_count,
        frame_width,
        frame_height,
        frame_center_x,
        frame_center_y,
        arduino_lines=None,
        **extra,
    ):
        if arduino_lines is None:
            arduino_lines = []

        self.logger.log(
            frame_index=self.frame_index,
            event=event,

            face_detected=face_detected,
            stable_face_detected=stable_face_detected,
            recent_detection_count=recent_detection_count,

            frame_width=frame_width,
            frame_height=frame_height,
            frame_center_x=frame_center_x,
            frame_center_y=frame_center_y,

            arduino_line=" | ".join(arduino_lines),

            **self.arduino_state.snapshot(),
            **extra,
        )

    # -----------------------------
    # Main frame processing
    # -----------------------------

    def process_frame(self, frame):
        rgb_img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_detection.process(rgb_img)

        h_img, w_img, _ = frame.shape
        frame_center_x = int(w_img / 2)
        frame_center_y = int(h_img / 2)

        cv2.circle(frame, (frame_center_x, frame_center_y), 3, (0, 255, 0), 2)

        face_detected = bool(results.detections)
        self.recent_face_detections.append(face_detected)

        stable_face_detected = (
            self.is_face_stably_detected()
            if self.config["use_stable_detection"]
            else face_detected
        )

        recent_detection_count = sum(self.recent_face_detections)

        arduino_lines = self.read_arduino_lines()

        if not face_detected:
            self.reset_pd_controller()

            self.log_common_frame_state(
                event="no_face",
                face_detected=False,
                stable_face_detected=stable_face_detected,
                recent_detection_count=recent_detection_count,
                frame_width=w_img,
                frame_height=h_img,
                frame_center_x=frame_center_x,
                frame_center_y=frame_center_y,
                arduino_lines=arduino_lines,
            )

            self._draw_status(frame, "no_face", None)
            print("no face detected")
            return frame

        if not stable_face_detected:
            self.reset_pd_controller()

            self.log_common_frame_state(
                event="unstable_face",
                face_detected=True,
                stable_face_detected=False,
                recent_detection_count=recent_detection_count,
                frame_width=w_img,
                frame_height=h_img,
                frame_center_x=frame_center_x,
                frame_center_y=frame_center_y,
                arduino_lines=arduino_lines,
            )

            self._draw_status(frame, "unstable_face", None)
            print("no stable face detected")
            return frame

        detection = self.get_largest_detection(results.detections, w_img, h_img)
        bboxC = detection.location_data.relative_bounding_box

        x = int(bboxC.xmin * w_img)
        y = int(bboxC.ymin * h_img)
        w = int(bboxC.width * w_img)
        h = int(bboxC.height * h_img)

        raw_face_center_x = x + int(w / 2)
        raw_face_center_y = y + int(h / 2)

        if self.config["use_smoothing"]:
            if self.smoothed_face_x is None:
                self.smoothed_face_x = raw_face_center_x
                self.smoothed_face_y = raw_face_center_y
            else:
                alpha = self.config["smoothing_alpha"]
                self.smoothed_face_x = (
                    alpha * raw_face_center_x
                    + (1 - alpha) * self.smoothed_face_x
                )
                self.smoothed_face_y = (
                    alpha * raw_face_center_y
                    + (1 - alpha) * self.smoothed_face_y
                )
        else:
            self.smoothed_face_x = raw_face_center_x
            self.smoothed_face_y = raw_face_center_y

        horizontal_distance = self.smoothed_face_x - frame_center_x
        vertical_distance = self.smoothed_face_y - frame_center_y

        angle_error = self.calculate_pan_angle(horizontal_distance, w_img)
        normalized_error = self.calculate_normalized_error(
            horizontal_distance,
            w_img,
        )

        within_dead_zone = abs(angle_error) <= self.config["dead_zone"]

        event = ""
        pan_delta = 0
        p_term = ""
        d_term = ""
        error_velocity = ""

        command = ""
        command_sent = False
        send_skipped_reason = ""
        time_since_last_send_s = ""

        if within_dead_zone:
            event = "center"
            self.reset_pd_controller()
            print(f"center, angle error: {angle_error:.2f}°")

        else:
            controller_mode = self.config["controller_mode"]

            if controller_mode == "none":
                event = "observe"
                print(f"observe only, angle error: {angle_error:.2f}°")

            elif controller_mode == "fixed":
                event = "control_fixed"

                control_result = self.calculate_pan_delta_fixed(angle_error)
                pan_delta = control_result["pan_delta"]
                p_term = control_result["p_term"]
                d_term = control_result["d_term"]
                error_velocity = control_result["error_velocity"]

                command = f"PAN:{pan_delta}"
                send_result = self.send_command(command)

                command_sent = send_result["sent"]
                send_skipped_reason = send_result["reason"]
                time_since_last_send_s = send_result["time_since_last_send_s"]
                arduino_lines.extend(send_result["arduino_lines"])

                print(
                    f"Fixed control, angle error: {angle_error:.2f}°, "
                    f"pan delta: {pan_delta}°"
                )

            elif controller_mode == "p":
                event = "control_p"

                control_result = self.calculate_pan_delta_p(angle_error)
                pan_delta = control_result["pan_delta"]
                p_term = control_result["p_term"]
                d_term = control_result["d_term"]
                error_velocity = control_result["error_velocity"]

                command = f"PAN:{pan_delta}"
                send_result = self.send_command(command)

                command_sent = send_result["sent"]
                send_skipped_reason = send_result["reason"]
                time_since_last_send_s = send_result["time_since_last_send_s"]
                arduino_lines.extend(send_result["arduino_lines"])

                print(f"P control, angle error: {angle_error:.2f}°, pan delta: {pan_delta}°")

            elif controller_mode == "pd":
                event = "control_pd"

                control_result = self.calculate_pan_delta_pd(angle_error)
                pan_delta = control_result["pan_delta"]
                p_term = control_result["p_term"]
                d_term = control_result["d_term"]
                error_velocity = control_result["error_velocity"]

                command = f"PAN:{pan_delta}"
                send_result = self.send_command(command)

                command_sent = send_result["sent"]
                send_skipped_reason = send_result["reason"]
                time_since_last_send_s = send_result["time_since_last_send_s"]
                arduino_lines.extend(send_result["arduino_lines"])

                print(
                    f"PD control, angle error: {angle_error:.2f}°, "
                    f"pan delta: {pan_delta}°, p: {p_term:.2f}, d: {d_term:.2f}"
                )

            else:
                raise ValueError(f"Unsupported controller mode: {controller_mode}")

        self.log_common_frame_state(
            event=event,

            face_detected=True,
            stable_face_detected=stable_face_detected,
            recent_detection_count=recent_detection_count,

            frame_width=w_img,
            frame_height=h_img,
            frame_center_x=frame_center_x,
            frame_center_y=frame_center_y,

            arduino_lines=arduino_lines,

            bbox_x=x,
            bbox_y=y,
            bbox_w=w,
            bbox_h=h,

            raw_face_center_x=raw_face_center_x,
            raw_face_center_y=raw_face_center_y,
            smoothed_face_center_x=round(self.smoothed_face_x, 3),
            smoothed_face_center_y=round(self.smoothed_face_y, 3),

            horizontal_distance=round(horizontal_distance, 3),
            vertical_distance=round(vertical_distance, 3),
            angle_error=round(angle_error, 6),
            normalized_error=round(normalized_error, 6),
            within_dead_zone=within_dead_zone,

            p_term=round(p_term, 6) if p_term != "" else "",
            d_term=round(d_term, 6) if d_term != "" else "",
            error_velocity=round(error_velocity, 6) if error_velocity != "" else "",

            pan_delta=pan_delta,
            command=command,
            command_sent=command_sent,
            send_skipped_reason=send_skipped_reason,
            time_since_last_send_s=(
                round(time_since_last_send_s, 6)
                if time_since_last_send_s != ""
                else ""
            ),
        )

        cv2.circle(
            frame,
            (int(self.smoothed_face_x), int(self.smoothed_face_y)),
            3,
            (0, 0, 255),
            2,
        )
        cv2.rectangle(frame, (x, y), (x + w, y + h), (80, 48, 230), 2)

        self._draw_status(frame, event, angle_error)

        return frame

    def _draw_status(self, frame, event, angle_error):
        cv2.putText(
            frame,
            f"version: {self.config['version']}",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )

        cv2.putText(
            frame,
            f"event: {event}",
            (20, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (255, 255, 255),
            2,
        )

        if angle_error is not None:
            cv2.putText(
                frame,
                f"error: {angle_error:.2f} deg",
                (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (255, 255, 255),
                2,
            )

    def run(self):
        self.setup()

        video_capture = cv2.VideoCapture(self.config["camera_index"])

        try:
            while True:
                ret, frame = video_capture.read()

                if ret is False:
                    break

                self.frame_index += 1

                frame = self.process_frame(frame)

                cv2.imshow("cameraman", frame)

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

        finally:
            video_capture.release()
            cv2.destroyAllWindows()
            self.close()


def run_tracker(config):
    tracker = PanTiltTracker(config)
    tracker.run()
