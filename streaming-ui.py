# setup series port

# read from http stream
# define event callback (unpack the text, and send to series port)


import serial
import time

arduino = serial.Serial('/dev/cu.usbmodem11101', SERIES_BAUD, timeout=1)
time.sleep(2)

arduino.reset_input_buffer()

