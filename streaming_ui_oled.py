import serial
import time
import requests
import json

SERIES_BAUD = 115200
arduino = serial.Serial('/dev/cu.usbmodem1301', SERIES_BAUD, timeout=1)
time.sleep(2)

arduino.reset_input_buffer()

def sanitise_text(text):
    return 

def send_message(event):
    event_type = event.get("type")

    # 1. 匹配你的真实元数据 {"type":"meta","source":"agentic-coding.md",...}
    if event_type == "meta":
        source = event.get("source", "unknown")
        total_chars = event.get("totalChars", 0)
        print(f"\n[META] Source: {source}, Total Chars: {total_chars}")
        
        # 协议格式：META:文件名|总字数\n
        meta_cmd = f"META:{source}|{total_chars}\n"
        arduino.write(meta_cmd.encode('utf-8'))
        arduino.flush()
        return

    # 2. 流结束
    if event_type == "done":
        print("\n[META] Stream Done.")
        arduino.write(b"DONE:\n")
        arduino.flush()
        return

    # 3. 匹配你的真实流事件 {"type":"assistant_delta","text":"..."}
    if event_type == "assistant_delta":
        text = event.get("text", "")
        if not text:
            return

        print(text, end="", flush=True)
        
        # 严格封装：TXT: + 文本内容 + \n
        txt_cmd = f"TXT:{text}\n" 
        arduino.write(txt_cmd.encode('utf-8'))
        arduino.flush()
        time.sleep(0.5)

url = "http://127.0.0.1:8788/api/stream"

def streaming_display():
    print("Connecting to stream...")
    try:
        with requests.post(url, json={}, stream=True) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                event = json.loads(line)
                send_message(event)
    except Exception as e:
        print(f"\nError: {e}")

if __name__ == "__main__":
    streaming_display()