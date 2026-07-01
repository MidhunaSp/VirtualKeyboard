# AI-Powered Virtual Keyboard ✋⌨️

Touch-free typing and mouse control using real-time hand tracking.
Built with **Python, OpenCV, MediaPipe, NumPy, and pynput**.

## Features

- 🖐️ Real-time hand tracking & gesture recognition (MediaPipe Hands)
- ⌨️ Gesture-based typing — two styles:
  - **Dwell typing**: hover your index fingertip over a key for a
    configurable amount of time to "press" it
  - **Pinch typing**: bring thumb and index finger together while
    pointing at a key
- 🖱️ Full mouse control: move, click (pinch), drag (hold pinch), scroll
  (two-finger vertical swipe)
- ⚡ Gesture shortcuts: Space, Backspace, Enter, Shift
- 🔁 Hands-free mode switching: hold a thumbs-up for ~1s to toggle
  between Typing and Mouse mode
- 🎛️ Interactive calibration screen for pinch sensitivity, dwell
  speed, and mouse smoothing — settings persist to `calibration.json`

## Project Structure

```
virtual_keyboard/
├── requirements.txt
├── README.md
└── src/
    ├── main.py               # entry point / app loop
    ├── config.py             # default settings + load/save calibration.json
    ├── hand_tracker.py        # MediaPipe wrapper: landmarks, pinch, thumbs-up
    ├── virtual_keyboard.py    # on-screen keyboard UI + typing gesture logic
    ├── mouse_controller.py    # cursor movement, click/drag, scroll
    └── calibration.py         # interactive trackbar calibration screen
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

> **macOS users**: grant your terminal/IDE "Accessibility" and "Camera"
> permissions in System Settings, or pynput/cv2 won't be able to
> control the mouse/keyboard or read the webcam.

## Run

```bash
cd src
python main.py
```

Run calibration on first launch (recommended):

```bash
python main.py --calibrate
```

Other useful flags:

```bash
python main.py --camera 1              # use a different webcam
python main.py --typing-mode pinch     # start in pinch-typing style instead of dwell
```

## Controls (in-app)

| Key | Action |
|---|---|
| `m` | Manually toggle Typing / Mouse mode |
| `p` | Toggle typing style (dwell ↔ pinch) |
| `c` | Re-open the calibration screen |
| `l` | Toggle hand landmark overlay |
| `q` / `ESC` | Quit |

**Gesture-only mode switch**: hold a 👍 thumbs-up for ~1 second.

## How It Works

1. **Hand tracking** (`hand_tracker.py`) — MediaPipe returns 21 3D
   landmarks per hand each frame. We derive higher-level signals from
   these: a scale-normalized pinch distance (thumb tip ↔ index tip),
   a thumbs-up heuristic, and which fingers are currently extended.
2. **Typing mode** (`virtual_keyboard.py`) — an on-screen QWERTY
   layout is generated and centered in the frame. Every frame, we
   check whether the fingertip is over a key and either:
   - accumulate dwell time until it crosses `dwell_time`, or
   - fire immediately on a detected pinch release,
   then send the keystroke through `pynput.keyboard`.
3. **Mouse mode** (`mouse_controller.py`) — the index fingertip
   position is mapped from a central "active zone" of the camera
   frame to full screen coordinates, exponentially smoothed to reduce
   jitter, and sent to the OS via `pynput.mouse`. A pinch that
   releases quickly is a click; a pinch held longer becomes a
   press-and-drag.
4. **Calibration** (`calibration.py`) — live trackbars let you watch
   your own pinch distance in real time while tuning the threshold,
   so the click detection matches your hand size and camera distance.

## Tuning Tips

- If clicks/keystrokes fire too easily: lower **pinch threshold** in
  calibration.
- If dwell typing feels sluggish or fires too fast: adjust
  **dwell_time** in `config.py` (or the calibration screen).
- If the cursor feels jittery: increase **mouse_smoothing** (trades
  responsiveness for stability).
- If you have to reach uncomfortably far to hit the screen edges in
  Mouse mode: shrink the `active_box` margins in
  `mouse_controller.py`.

## Known Limitations / Ideas for Improvement

- Single-hand tracking by default (`max_num_hands: 1` in
  `config.py`) — bump this to 2 for two-handed shortcuts.
- Thumbs-up detection is a simple heuristic; a small classifier
  trained on your own gesture data would be more robust.
- No on-screen numeric/symbol layer toggle yet — could add a
  `123` key that swaps `ROWS` in `virtual_keyboard.py`.
- Works best in consistent, well-lit conditions since MediaPipe's
  accuracy depends on clear hand visibility.

## Tech Stack

Python · OpenCV · MediaPipe · NumPy · pynput · pyautogui (for screen
resolution detection)
