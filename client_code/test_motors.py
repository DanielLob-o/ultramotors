from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory
from time import sleep

# Pins
PAN_PIN = 18
TILT_PIN = 19

# Configuration
SERVO_CFG = {
    "min_angle": -90,
    "max_angle": 90,
    "min_pulse_width": 0.0005,
    "max_pulse_width": 0.0025
}

def run_test():
    print("--- ⚙️ STARTING SERVO TEST ---")
    
    # Try hardware PWM
    factory = None
    try:
        factory = PiGPIOFactory()
        print("✅ Using PiGPIOFactory")
    except Exception:
        print("⚠️ PiGPIO daemon not running. Using software PWM.")

    print(f"Connecting to Pan: GPIO {PAN_PIN}, Tilt: GPIO {TILT_PIN}")
    try:
        pan = AngularServo(PAN_PIN, pin_factory=factory, **SERVO_CFG)
        tilt = AngularServo(TILT_PIN, pin_factory=factory, **SERVO_CFG)
    except Exception as e:
        print(f"❌ Init Error: {e}")
        return

    try:
        while True:
            print("Target: CENTER (0°)")
            pan.angle = 0
            tilt.angle = 0
            sleep(1.5)

            print("Target: RIGHT/UP (+90°)")
            pan.angle = 90
            tilt.angle = 90
            sleep(1.5)

            print("Target: CENTER (0°)")
            pan.angle = 0
            tilt.angle = 0
            sleep(1.5)

            print("Target: LEFT/DOWN (-90°)")
            pan.angle = -90
            tilt.angle = -90
            sleep(1.5)

    except KeyboardInterrupt:
        print("\n🛑 Stopped")
        pan.angle = 0
        tilt.angle = 0
        sleep(0.5)
        pan.close()
        tilt.close()

if __name__ == "__main__":
    run_test()