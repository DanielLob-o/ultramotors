import json
import sys
import struct
from time import sleep
from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory

# Function to safely create servo instances
def create_servo(pin, factory):
    return AngularServo(
        pin,
        min_angle=-90,
        max_angle=90,
        min_pulse_width=0.0005,
        max_pulse_width=0.0025,
        pin_factory=factory
    )

class MotorController:
    def __init__(self):
        print("⚙️ Motor Controller Initialized", file=sys.stderr)
        self.buffer = b""

        # Hardware Pins
        self.PAN_PIN = 18
        self.TILT_PIN = 19

        # PID Tuning
        self.KP = 0.04
        self.KI = 0.002
        self.MAX_INTEGRAL = 20

        # State
        self.current_pan = 0.0
        self.current_tilt = 0.0
        self.pan_integral = 0.0
        self.tilt_integral = 0.0

        # Setup GPIO
        self.factory = None
        try:
            self.factory = PiGPIOFactory()
            print("✅ Using PiGPIOFactory", file=sys.stderr)
        except Exception:
            print("⚠️ PiGPIO daemon not running. Using default software PWM.", file=sys.stderr)

        try:
            self.pan_servo = create_servo(self.PAN_PIN, self.factory)
            self.tilt_servo = create_servo(self.TILT_PIN, self.factory)
            
            # Center on startup
            self.pan_servo.angle = 0
            self.tilt_servo.angle = 0
            
            print("✅ Servo GPIO Setup Complete", file=sys.stderr)
        except Exception as e:
            print(f"❌ GPIO Init Error: {e}", file=sys.stderr)

    def process_incoming_data(self, data_bytes):
        self.buffer += data_bytes
        while True:
            if len(self.buffer) < 4: break
            msg_length = struct.unpack('!I', self.buffer[:4])[0]
            if len(self.buffer) < 4 + msg_length: break
            
            payload = self.buffer[4 : 4 + msg_length]
            self.buffer = self.buffer[4 + msg_length :]
            
            self.handle_json_payload(payload)

    def handle_json_payload(self, json_bytes):
        try:
            msg = json.loads(json_bytes.decode('utf-8'))
            err_x = msg.get("err_x", 0)
            err_y = msg.get("err_y", 0)

            self.pan_integral = max(-self.MAX_INTEGRAL, min(self.MAX_INTEGRAL, self.pan_integral + err_x))
            self.tilt_integral = max(-self.MAX_INTEGRAL, min(self.MAX_INTEGRAL, self.tilt_integral + err_y))

            # Calculate corrections
            pan_adj = (err_x * self.KP) + (self.pan_integral * self.KI)
            tilt_adj = (err_y * self.KP) + (self.tilt_integral * self.KI)

            # Update Angles
            # Pan: Right is +90. Object Right (err_x > 0) -> Increase Angle
            self.current_pan += pan_adj
            
            # Tilt: Up is +90. Object Above (err_y < 0, assuming top-left origin) 
            # Object Above (err_y > 0 if bottom-left origin).
            # assuming standard image coords (Top=0): Object Above means err_y is negative.
            # we need to look UP (+ angle). So we SUBTRACT the negative error.
            self.current_tilt -= tilt_adj

            self.current_pan = max(-90, min(90, self.current_pan))
            self.current_tilt = max(-90, min(90, self.current_tilt))

            # Apply
            if hasattr(self, 'pan_servo'):
                self.pan_servo.angle = self.current_pan
            if hasattr(self, 'tilt_servo'):
                self.tilt_servo.angle = self.current_tilt

        except (ValueError, json.JSONDecodeError):
            pass
        except Exception as e:
            print(f"❌ Servo Loop Error: {e}", file=sys.stderr)