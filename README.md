# UltraMotors: Intelligent Tracking Turret

This project implements an autonomous object-tracking turret system using a Raspberry Pi client and a Elixir/Python backend.

## System Architecture

The system is divided into two main components:

### 1. The Client (Raspberry Pi)
*   **Hardware**: Raspberry Pi with a Pan-Tilt DSServo mount and a camera mounted on top.
*   **Role**:
    *   Captures live video feed.
    *   Sends video data to the server via TCP.
    *   Receives targeting coordinates from the server.
    *   **Motor Control**: Dynamically adjusts the Pan and Tilt servos to keep the target centered in the frame.

### 2. The Server
*   **Core**: Built with **Elixir**, handling high-concurrency TCP connections and data routing.
*   **AI Processing**: A **Python Worker** running **YOLO (You Only Look Once)** performs real-time object recognition on the incoming video stream.
*   **Logic**: Calculates the error (distance from center) for detected targets and sends correction commands back to the client.

## How It Works
1.  **See**: The Pi Camera captures a frame.
2.  **Send**: The frame is sent to the Server.
3.  **Think**: The Server's Python worker detects objects (e.g., people, pets) and calculates how far off-center they are.
4.  **Act**: The Server sends error values (`err_x`, `err_y`) back to the Pi.
5.  **Move**: The Pi adjusts the servo motors to "zero out" the error, physically moving the camera to track the target.
