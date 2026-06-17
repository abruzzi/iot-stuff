# setup series port

# read from http stream
# define event callback (unpack the text, and send to series port)

import serial
import time
import requests
import json

# SERIES_BAUD=115200

# arduino = serial.Serial('/dev/cu.usbmodem11101', SERIES_BAUD, timeout=1)
# time.sleep(2)

# arduino.reset_input_buffer()

def normalise_buffer(text):
    return " ".join(
        text
        .replace("|", "/")
        .replace("\r", " ")
        .replace("\n", " ")
        .split()
    )

def clean_for_lcd(text):
    return text.replace("\r", " ").replace("\n", " ")

def fit_line(text, width=16):
    return text[:width].ljust(width)

display_buffer = ""

def prepare_lcd_lines(chunk):
    global display_buffer

    display_buffer += chunk
    readable_buffer = normalise_buffer(display_buffer)

    window = readable_buffer[-32:].rjust(32)

    l1 = fit_line(window[:16])
    l2 = fit_line(window[16:32])

    return l1, l2

def send_message(event):
    event_type = event.get("type")

    if event_type == "meta":
        print(event.get("source"))
        return

    if event_type == "done":
        print("done")
        return

    text = event.get("text", "")
    l1, l2 = prepare_lcd_lines(text)

    print(f"[{l1}]")
    print(f"[{l2}]")
    print()

    # arduino.write("{command}".encode('utf-8'))
    # arduino.flush()

    # if arduino.in_waiting > 0:
    #     try:
    #         line = arduino.readline().decode("utf-8", errors="ignore").strip()
    #         print("arduino:", line)
    #     except Exception:
    #         pass


url = "http://127.0.0.1:8788/api/stream"

def get_response():
    # curl -N -X POST http://127.0.0.1:8788/api/stream -H "Content-Type: application/json" -d '{}'

    with requests.post(url, json={}, stream=True) as response:
        response.raise_for_status()

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            event = json.loads(line)
            send_message(event)


get_response()