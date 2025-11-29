import socket
import struct
import cv2
import select 
from picamera2 import Picamera2
from turret_motors import MotorController

SERVER_IP = '192.168.1.142'
SERVER_PORT = 9999

motors = MotorController()

# --- CAMERA SETUP ---
camera = Picamera2()
config = camera.create_preview_configuration(
    main={"size": (640, 480), "format": "RGB888"},
    controls={
        "FrameDurationLimits": (33333, 33333),
        "AfMode": 0, 
        "LensPosition": 0.0
    }
)
camera.configure(config)
camera.start()

# --- NETWORK SETUP ---
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    print(f"📡 Connecting to {SERVER_IP}...", flush=True)
    client_socket.connect((SERVER_IP, SERVER_PORT))
    client_socket.setblocking(False) # <---- !!!CRITICAL: Set socket to non-blocking mode!!!
    print("✅ Connected! Starting Stream...", flush=True)

    while True:
        # capture frame and send
        frame = camera.capture_array()
        ret, encoded_frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        data = encoded_frame.tobytes()
        
        try:
            packet = struct.pack("!I", len(data)) + data
            client_socket.sendall(packet)
        except BlockingIOError:
            pass # socket buffer full, skip frame this is to prevent lag

        # CHECK FOR COMMANDS (NON-THREADED)
        # select.select([read_list], [write_list], [error_list], timeout)
        # Timeout = 0.0 means "Check instantly and don't wait"
        readable, _, _ = select.select([client_socket], [], [], 0.0)

        if readable:
            try:
                # I use 1024 bytes because is enough for {"pan": "RIGHT", "tilt": "UP"}
                response_data = client_socket.recv(1024)
                
                if not response_data:
                    print("❌ Server closed connection", flush=True)
                    break
                
                motors.process_incoming_data(response_data)
                
            except BlockingIOError:
                pass 

except KeyboardInterrupt:
    print("\nStopping...")
except Exception as e:
    print(f"\n❌ Client Error: {e}", flush=True)

finally:
    client_socket.close()
    camera.stop()