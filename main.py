import cv2
import mediapipe as mp
import asyncio
import websockets
import json
import urllib.request
import threading
import time

# -------------------- MediaPipe setup --------------------
url = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
try:
    open("pose_landmarker.task")
except:
    urllib.request.urlretrieve(url, "pose_landmarker.task")

base_options = mp.tasks.BaseOptions(model_asset_path="pose_landmarker.task")
options = mp.tasks.vision.PoseLandmarkerOptions(base_options=base_options)
detector = mp.tasks.vision.PoseLandmarker.create_from_options(options)

# -------------------- Shared state --------------------
latest_landmarks = []
latest_frame = None
clients = set()
running = True

# -------------------- WebSocket --------------------
async def handler(websocket):
    print("Client connected")
    clients.add(websocket)
    try:
        await websocket.wait_closed()
    finally:
        clients.discard(websocket)
        print("Client disconnected")

async def broadcast_loop():
    while running:
        if clients and latest_landmarks:
            data = json.dumps(latest_landmarks)
            await asyncio.gather(
                *[c.send(data) for c in clients],
                return_exceptions=True
            )
        await asyncio.sleep(1 / 30)

# -------------------- Camera thread --------------------
def camera_loop():
    global latest_landmarks, latest_frame, running

    cap = cv2.VideoCapture(0)
    while running:
        ret, frame = cap.read()
        if not ret:
            continue

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_image)

        if result.pose_landmarks:
            latest_landmarks = [
                {"x": l.x, "y": l.y, "z": l.z}
                for l in result.pose_landmarks[0]
            ]

        latest_frame = frame
        time.sleep(0.001)

    cap.release()

# -------------------- Main --------------------
async def main():
    global running

    threading.Thread(target=camera_loop, daemon=True).start()

    async with websockets.serve(handler, "localhost", 8765):
        print("WebSocket server running at ws://localhost:8765")
        broadcaster = asyncio.create_task(broadcast_loop())

        while running:
            if latest_frame is not None:
                cv2.imshow("Pose", latest_frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                running = False
                break

            await asyncio.sleep(0.001)

        broadcaster.cancel()

    cv2.destroyAllWindows()

asyncio.run(main())