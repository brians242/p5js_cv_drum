# Motion Drum

A little project that lets you play drums with your body. It uses your webcam to track your wrists, and when you swing one down into the drum zone on screen, it plays a sound. It also records 4 seconds of whatever you just played and loops it back so you can layer on top of yourself.

---

## How it works

There are two parts:

- **`server.py`** opens your webcam, runs pose detection on each frame, and sends your body landmark positions to the browser over a WebSocket.
- **`index.html`** receives those landmarks, draws your skeleton on screen, listens for wrist strikes, plays sounds, and handles the looping.

---

## Setup

### Python dependencies

```bash
pip install opencv-python mediapipe websockets
```

### Running it

First, start the server:

```bash
python main.py
```

The first time you run it, it'll download the MediaPipe pose model (~3MB) automatically. A webcam preview window will pop up — press `q` there when you want to quit.

Then open `index.html` in your browser. The easiest way I found to do this was using the **Live Server extension in VSCode** (right-click the file → "Open with Live Server"). Just opening the file directly as a local file can cause issues with the WebSocket connection, so Live Server is what I'd recommend.

If you open `index.html` directly in the browser or through the localhost, it may not work as it didn't early on in my development. It might be worth a shot if you don't want to go through all those steps!

Once it loads, **click on the page first** — browsers require a click before they'll play audio.

---

## Playing

Stand so your upper body is visible to the camera. Once it picks you up, you'll see your skeleton drawn on screen. Swing either wrist **downward** into the blue **DRUM ZONE** at the bottom to trigger a hit.

The indicator in the top-right corner shows what mode you're in:
- 🔴 **Red** — recording your hits for 4 seconds
- 🔵 **Blue** — playing back what you just recorded while you keep playing on top

---

## Code walkthrough

### server.py

**Model download** — At the top, the script checks if `pose_landmarker.task` exists locally and downloads it from Google if not. This only happens once.

**Camera loop** — Runs in a background thread. It grabs frames from your webcam using OpenCV, converts each one to RGB, and passes it to MediaPipe. If a pose is detected, it pulls the 33 landmark coordinates (each with x, y, z values between 0 and 1) and stores them in `latest_landmarks`.

**WebSocket handler** — Any browser that connects gets added to a `clients` set. When they disconnect, they're removed. Simple as that.

**Broadcast loop** — Runs at ~30fps. If there are any connected clients and landmarks to send, it serializes the landmark list as JSON and fires it to everyone at once.

**Main** — Kicks off the camera thread, starts the WebSocket server on port 8765, and runs a small display loop that shows the webcam preview. Pressing `q` sets `running = False` which shuts everything down cleanly.

---

### index.html

**WebSocket connection** — `connect()` opens a connection to the Python server and listens for messages. Each message is a JSON array of landmark objects which gets stored in `landmarks`. If the connection drops, it retries every second.

**`setup()`** — Creates the canvas, initializes the `MonoSynth` for audio, and calculates the drum zone position based on the current window size.

**`handleWrist()`** — Called once per frame for each wrist. It reads the wrist's current position, draws a dot on screen, and checks if the wrist moved downward fast enough (based on `STRIKE_THRESHOLD`) and is inside the drum zone. If so, it triggers a drum hit and logs the timestamp if recording is active.

**`playDrum()`** — Plays a short "C2" note on the synth. Volume can be passed in — live hits play at 0.9, mirrored playback plays at 0.5 so you can hear the difference.

**`updateRecording()`** — Manages the 4-second record/mirror cycle. When the recording window ends, it copies `recordBuffer` into `mirrorBuffer`, clears the record buffer, and flips the mode. Then after another 4 seconds, it starts recording again.

**`playMirror()`** — During the mirror phase, this checks every frame if the elapsed time is close to any stored timestamp in `mirrorBuffer` (within 20ms). If it matches, it fires a drum hit at half volume.

**`drawSkeleton()`** — Loops through the `CONNECTIONS` array (pairs of landmark indices) and draws lines between them in green. Also draws a small dot at every landmark. The x coordinate is flipped (`1 - x`) so it mirrors what you see in a webcam preview.

**`drawDrumZone()`** — Just draws the blue rectangle at the bottom of the screen with the "DRUM ZONE" label.

**`draw()`** — The main p5.js loop, called every frame. Clears the background, calls all the above functions in order, and draws the recording indicator dot in the corner.

---

## Tweaking

A few things you might want to adjust:

- **`STRIKE_THRESHOLD`** (default `18`) — how fast your wrist needs to move downward to count as a hit. Lower = more sensitive.
- **`RECORD_DURATION`** (default `4000`) — loop length in milliseconds.
- **`cv2.VideoCapture(0)`** in `server.py` — change `0` to `1` or `2` if you have multiple cameras and it's picking up the wrong one.

---

## Troubleshooting

**Stuck on "Move to begin..."**
Make sure `server.py` is actually running. Also check that your upper body is in frame — it needs to see your shoulders, elbows, and wrists.

**No sound**
Click on the canvas first. Browsers block audio until there's been a user interaction.

**WebSocket errors in the browser console**
Try Live Server in VSCode if you haven't already — that fixed it for me.

---

## Credits

- [MediaPipe](https://developers.google.com/mediapipe/solutions/vision/pose_landmarker) — pose detection
- [p5.js](https://p5js.org/) — canvas + audio
- [websockets](https://websockets.readthedocs.io/) — Python WebSocket server
- [OpenCV](https://opencv.org/) — webcam capture
