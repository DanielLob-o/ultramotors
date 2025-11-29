import json
import sys
import struct

class MotorController:
    def __init__(self):
        print("⚙️ Motor Controller Initialized", file=sys.stderr)
        self.buffer = b"" # for partial data packets

    def process_incoming_data(self, data_bytes):
        """
        Takes raw bytes from the socket, handles the 4-byte Elixir header,
        and decodes JSON commands.
        """
        self.buffer += data_bytes
        
        while True:
            # do we have at least 4 bytes for the header?
            if len(self.buffer) < 4:
                break 
            
            # decode the length (First 4 bytes, Big Endian Int)
            msg_length = struct.unpack('!I', self.buffer[:4])[0]
            
            # do we have the full message body yet?
            if len(self.buffer) < 4 + msg_length:
                break # wait for the rest of the message
            
            payload_data = self.buffer[4 : 4 + msg_length]
            
            # advance the stream
            self.buffer = self.buffer[4 + msg_length :]
            self.handle_json_payload(payload_data)

    def handle_json_payload(self, json_bytes):
        try:
            message = json_bytes.decode('utf-8')
            command = json.loads(message)
            
            pan = command.get("pan", "HOLD")
            tilt = command.get("tilt", "HOLD")
            
            self.move(pan, tilt)
            
        except json.JSONDecodeError:
            print(f"⚠️ JSON Error: Could not decode {json_bytes}", file=sys.stderr)
        except Exception as e:
            print(f"⚠️ Execution Error: {e}", file=sys.stderr)

    def move(self, pan, tilt):
        # only print if there is action to avoid spamming "HOLD"
        if pan != "HOLD" or tilt != "HOLD":
            print(f"🤖 ACTING -> Pan: {pan} | Tilt: {tilt}", flush=True)
            