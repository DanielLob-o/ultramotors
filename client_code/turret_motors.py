import json
import sys
import struct
from gpiozero import OutputDevice
from time import sleep

# --- STEPPER DRIVER CLASS ---
class StepperMotor:
    def __init__(self, pins, step_delay=0.002):
        self.pins = [OutputDevice(pin) for pin in pins]
        self.step_delay = step_delay
        self.step_index = 0
        self.sequence = [
            [1, 1, 0, 0], [0, 1, 1, 0], [0, 0, 1, 1], [1, 0, 0, 1]
        ]
        self.seq_len = len(self.sequence)

    def step(self, steps):
        direction = 1 if steps > 0 else -1
        for _ in range(abs(steps)):
            self.step_index = (self.step_index + direction) % self.seq_len
            pattern = self.sequence[self.step_index]
            for i in range(4):
                if pattern[i]: self.pins[i].on()
                else: self.pins[i].off()
            sleep(self.step_delay)

    def stop(self):
        for pin in self.pins: pin.off()

# --- MAIN CONTROLLER (PI) ---
class MotorController:
    def __init__(self):
        print("⚙️ Motor Controller Initialized (PI Control)", file=sys.stderr)
        self.buffer = b""

        # --- PINS ---
        PAN_PINS = [17, 18, 26, 16]
        TILT_PINS = [23, 24, 25, 8]

        # --- PI TUNING ---
        
        # proportional part (how fast it goes)
        # Higher = Faster reaction, but wobbles
        self.KP = 0.07   

        # integral part, error correction
        self.KI = 0.001

        #lLimits
        self.MAX_STEPS = 10 
        
        # integral windup limit: prevents the "memory" from getting too huge
        # if the target is off-screen for a long time.
        self.MAX_INTEGRAL = 300 

        # --- STATE VARIABLES ---
        self.pan_integral = 0.01
        self.tilt_integral = 0.01

        try:
            self.pan_motor = StepperMotor(PAN_PINS)
            self.tilt_motor = StepperMotor(TILT_PINS)
            print("✅ GPIO Pins Setup Successfully", file=sys.stderr)
        except Exception as e:
            print(f"❌ GPIO Error: {e}", file=sys.stderr)

    def process_incoming_data(self, data_bytes):
        self.buffer += data_bytes
        while True:
            if len(self.buffer) < 4: break
            msg_length = struct.unpack('!I', self.buffer[:4])[0]
            if len(self.buffer) < 4 + msg_length: break
            
            payload_data = self.buffer[4 : 4 + msg_length]
            self.buffer = self.buffer[4 + msg_length :]
            
            self.handle_json_payload(payload_data)

    def handle_json_payload(self, json_bytes):
        try:
            message = json_bytes.decode('utf-8')
            command = json.loads(message)
            
            err_x = command.get("err_x", 0)
            err_y = command.get("err_y", 0)
            
            self.move_pi_controller(err_x, err_y)
            
        except json.JSONDecodeError:
            print(f"⚠️ JSON Error: {json_bytes}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ Motor Logic Error: {e}", file=sys.stderr)

    def move_pi_controller(self, err_x, err_y):
        # --- PAN CALCULATIONS ---
        
        # accumulate error
        self.pan_integral += err_x
        
        # anti-Windup (Clamp the Integral)
        # prevents the turret from spinning wildly after the target re-appears
        self.pan_integral = max(min(self.pan_integral, self.MAX_INTEGRAL), -self.MAX_INTEGRAL)
        
        # reset integral if we are basically on target
        # This stops the turret from "orbiting" the center due to old memory
        if abs(err_x) < 5: 
            self.pan_integral = 0

        # calculate Output (P + I)
        pan_output = ((err_x * self.KP) + (self.pan_integral * self.KI)) * -1


        # --- TILT CALCULATIONS ---
        self.tilt_integral += err_y
        self.tilt_integral = max(min(self.tilt_integral, self.MAX_INTEGRAL), -self.MAX_INTEGRAL)
        
        if abs(err_y) < 5: 
            self.tilt_integral = 0

        tilt_output = ((err_y * self.KP) + (self.tilt_integral * self.KI)) * -1


        # --- CONVERT TO INTEGER STEPS ---
        pan_steps = int(pan_output)
        tilt_steps = int(tilt_output)

        # --- SAFETY SPEED LIMIT ---
        pan_steps = max(min(pan_steps, self.MAX_STEPS), -self.MAX_STEPS)
        tilt_steps = max(min(tilt_steps, self.MAX_STEPS), -self.MAX_STEPS)

        # --- MOVE ---
        if pan_steps != 0:
            self.pan_motor.step(pan_steps)
        
        if tilt_steps != 0:
            self.tilt_motor.step(tilt_steps)

        # Debug logs (Uncomment to tune)
        if pan_steps != 0 or tilt_steps != 0:
             print(f"🤖 P:{err_x*self.KP:.1f} I:{self.pan_integral*self.KI:.1f} -> STEP {pan_steps}", flush=True)