import sys
import struct
import cv2
import numpy as np
import json
from ultralytics import YOLO
import os

# --- CONFIGURATION ---
SHOW_WINDOW = True 
PROCESS_EVERY_N_FRAMES = 15
TARGET_CLASSES = [15] 

#0 = Person

#14 = Bird

#15 = Cat

#16 = Dog

# --- HELPER: SEND DATA TO ELIXIR ---
def send_elixir(data_bytes):
    length = len(data_bytes)
    header = struct.pack('!I', length)
    sys.stdout.buffer.write(header)
    sys.stdout.buffer.write(data_bytes)
    sys.stdout.buffer.flush()

# setup model, use yolov10n.pt if your computer is GPU optimized
script_dir = os.path.dirname(os.path.abspath(__file__))
model_path = os.path.join(script_dir, "yolov8n.pt")

print(f"🚀 Loading YOLO from: {model_path}", file=sys.stderr)

try:
    if os.path.exists(model_path):
        model = YOLO(model_path)
    else:
        print(f"⚠️ Model not found, downloading...", file=sys.stderr)
        model = YOLO("yolov8n.pt") # default model
except Exception as e:
    print(f"❌ Error loading model: {e}", file=sys.stderr)
    sys.exit(1)

def read_exact(n):
    data = b''
    while len(data) < n:
        chunk = sys.stdin.buffer.read(n - len(data))
        if not chunk: return None
        data += chunk
    return data

def draw_hud(frame, center_x, center_y, width, height, err_x, err_y):
    """Draws a tactical crosshair and error data on the screen"""
    # Colors (RGB)
    GRAY = (100, 100, 100)
    CYAN = (255, 255, 0)
    RED = (0, 0, 255)
    GREEN = (0, 255, 0)
    
    # center crosshair with gap
    gap = 5
    length = 30
    # Horizontal
    cv2.line(frame, (center_x - length, center_y), (center_x - gap, center_y), GRAY, 1)
    cv2.line(frame, (center_x + gap, center_y), (center_x + length, center_y), GRAY, 1)
    # Vertical
    cv2.line(frame, (center_x, center_y - length), (center_x, center_y - gap), GRAY, 1)
    cv2.line(frame, (center_x, center_y + gap), (center_x, center_y + length), GRAY, 1)
    
    # error bars for visal feedback
    if err_x is not None and err_y is not None:
        cv2.line(frame, (center_x, center_y), (center_x + err_x, center_y), RED, 2)
        cv2.line(frame, (center_x + err_x, center_y), (center_x + err_x, center_y + err_y), RED, 2)
        
        # Background box for text to make it readable
        cv2.rectangle(frame, (10, 10), (200, 70), (0, 0, 0), -1) # Filled black box
        cv2.putText(frame, f"ERROR X: {err_x}", (20, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.6, CYAN, 2)
        cv2.putText(frame, f"ERROR Y: {err_y}", (20, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, CYAN, 2)

def main():
    send_elixir(b"READY")
    print(f"Python Worker Started", file=sys.stderr) 

    frame_count = 0
    last_results = [] 

    while True:
        try:
            header = read_exact(4)
            if not header: break
            img_size = struct.unpack('!I', header)[0]

            img_data = read_exact(img_size)
            if not img_data: break

            nparr = np.frombuffer(img_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if frame is None: continue

            h, w, _ = frame.shape
            center_x, center_y = w // 2, h // 2

            frame_count += 1
            
            # --- AI PROCESSING ---
            if frame_count % PROCESS_EVERY_N_FRAMES == 0:
                results = model(frame, verbose=False)
                last_results = [] 

                for result in results:
                    boxes = result.boxes
                    for box in boxes:
                        cls_id = int(box.cls[0])
                        if cls_id in TARGET_CLASSES:
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            
                            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                            err_x, err_y = cx - center_x, cy - center_y
                            
                            label_text = model.names[cls_id]
                            
                            last_results.append({
                                'box': [x1, y1, x2, y2],
                                'label': label_text,
                                'err_x': int(err_x),
                                'err_y': int(err_y),
                                'cx': cx, 
                                'cy': cy
                            })
                            # Track only first target
                            break 
            
            # --- PREPARE ELIXIR PAYLOAD ---
            elixir_payload = []
            
            # --- VISUALIZATION LAYER ---
            active_err_x = None
            active_err_y = None

            if len(last_results) > 0:
                # Use the first target for the HUD error display
                active_err_x = last_results[0]['err_x']
                active_err_y = last_results[0]['err_y']

            if SHOW_WINDOW:
                draw_hud(frame, center_x, center_y, w, h, active_err_x, active_err_y)

            for item in last_results:
                elixir_payload.append({
                    "label": item['label'],
                    "err_x": item['err_x'],
                    "err_y": item['err_y']
                })

                if SHOW_WINDOW:
                    x1, y1, x2, y2 = item['box']
                    label = item['label']
                    # green box around target
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, label, (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

            # --- SEND & SHOW ---
            json_bytes = json.dumps(elixir_payload).encode('utf-8')
            send_elixir(json_bytes)

            if SHOW_WINDOW:
                cv2.imshow("Turret Brain (Hybrid)", frame)
                if cv2.waitKey(1) == ord('q'): break

        except Exception as e:
            print(f"Python Error: {e}", file=sys.stderr)
            break

if __name__ == "__main__":
    main()