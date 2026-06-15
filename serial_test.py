import serial
import time

arduino = serial.Serial("/dev/cu.usbmodem11301", 9600, timeout=1)

time.sleep(2)
arduino.reset_input_buffer()

def send(command):
    arduino.write(f"{command}\n".encode("utf-8"))
    arduino.flush()

    print("sent:", command)

    time.sleep(0.2)

    while arduino.in_waiting > 0:
        line = arduino.readline().decode("utf-8", errors="ignore").strip()
        print("arduino:", line)

send("LEFT")
time.sleep(1)

send("LEFT")
time.sleep(1)

send("RIGHT")
time.sleep(1)

send("RIGHT")

arduino.close()