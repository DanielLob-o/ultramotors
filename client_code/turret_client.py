import socket
import struct
import cv2
import select
from picamera2 import Picamera2
from turret_motors import MotorController

SERVER_IP = '192.168.1.142' 
SERVER_PORT = 9999

# Init Motors
motors = MotorController()

# Init Camera
try:
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
except IndexError:
    print("Error: No camera detected!", flush=True)
    exit(1)
except Exception as e:
    print(f"Error initializing camera: {e}", flush=True)
    exit(1)

# connect into server
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    print(f"Connecting to {SERVER_IP}...", flush=True)
    client_socket.connect((SERVER_IP, SERVER_PORT))
    client_socket.setblocking(False) 
    print("Connected! Starting Stream...", flush=True)

    while True:
        # Capture & Encode
        frame = camera.capture_array()
        ret, encoded_frame = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        data = encoded_frame.tobytes()
        
        # Send
        try:
            packet = struct.pack("!I", len(data)) + data
            client_socket.sendall(packet)
        except BlockingIOError:
            pass 
        
        # Receive
        readable, _, _ = select.select([client_socket], [], [], 0.0)
        if readable:
            try:
                response_data = client_socket.recv(1024)
                if not response_data:
                    print("Server closed connection", flush=True)
                    break
                motors.process_incoming_data(response_data)
            except BlockingIOError:
                pass 

except KeyboardInterrupt:
    print("\nStopping...")
except Exception as e:
    print(f"\nClient Error: {e}", flush=True)
finally:
    client_socket.close()
    camera.stop()