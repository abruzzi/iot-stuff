import serial
import time

PORT = "/dev/cu.usbmodem1301"
BAUD_RATE = 115200

with serial.Serial(PORT, BAUD_RATE, timeout=1) as ser:
    time.sleep(2)
    print(f"Connected to {PORT}")

    while True:
        line = ser.readline().decode("utf-8", errors="ignore").strip()
        if line:
            print(line)