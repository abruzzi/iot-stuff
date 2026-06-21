class ArduinoState:
    def __init__(self):
        self.latest_servo_angle = None
        self.latest_servo_previous_angle = None
        self.latest_servo_delta = None
        self.latest_command_received = None

    def parse_line(self, line):
        if line.startswith("SERVO_ANGLE:"):
            self.latest_servo_angle = self._parse_int_after_colon(line)

        elif line.startswith("SERVO_PREVIOUS_ANGLE:"):
            self.latest_servo_previous_angle = self._parse_int_after_colon(line)

        elif line.startswith("SERVO_DELTA:"):
            self.latest_servo_delta = self._parse_int_after_colon(line)

        elif line.startswith("COMMAND_RECEIVED:"):
            self.latest_command_received = line.split(":", 1)[1]

    def snapshot(self):
        return {
            "servo_angle": self.latest_servo_angle if self.latest_servo_angle is not None else "",
            "servo_previous_angle": (
                self.latest_servo_previous_angle
                if self.latest_servo_previous_angle is not None
                else ""
            ),
            "servo_delta": self.latest_servo_delta if self.latest_servo_delta is not None else "",
        }

    def _parse_int_after_colon(self, line):
        try:
            return int(line.split(":", 1)[1])
        except ValueError:
            return None
