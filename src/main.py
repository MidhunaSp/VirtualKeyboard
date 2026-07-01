"""
main.py
AI-Powered Virtual Keyboard - entry point.

Two modes, toggled by holding a thumbs-up gesture for ~1 second:
  TYPING mode - hover/pinch over the on-screen keyboard to type
  MOUSE mode  - index finger moves the cursor, pinch to click,
                two-finger vertical motion scrolls

Controls:
  m         - manually toggle typing/mouse mode
  p         - toggle between pinch-typing and dwell-typing
  c         - re-run calibration
  l         - toggle landmark drawing
  q / ESC   - quit
"""

import argparse
import sys
import time

import cv2

try:
    import pyautogui
    SCREEN_W, SCREEN_H = pyautogui.size()
except Exception:
    # Fallback if pyautogui / a display isn't available; mouse control
    # will simply be less accurate about screen bounds.
    SCREEN_W, SCREEN_H = 1920, 1080

from config import load_config, save_config
from hand_tracker import HandTracker, FPSCounter
from virtual_keyboard import VirtualKeyboard
from mouse_controller import GestureMouse
from calibration import run_calibration


def parse_args():
    p = argparse.ArgumentParser(description="AI-Powered Virtual Keyboard")
    p.add_argument("--calibrate", action="store_true", help="Run calibration screen on startup")
    p.add_argument("--camera", type=int, default=None, help="Override camera index")
    p.add_argument("--typing-mode", choices=["pinch", "dwell"], default="dwell",
                    help="Typing gesture style")
    return p.parse_args()


def main():
    args = parse_args()
    cfg = load_config()
    if args.camera is not None:
        cfg["camera_index"] = args.camera

    cap = cv2.VideoCapture(cfg["camera_index"])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg["frame_width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg["frame_height"])

    if not cap.isOpened():
        print("ERROR: Could not open camera. Check --camera index or permissions.")
        sys.exit(1)

    ok, sample_frame = cap.read()
    if not ok:
        print("ERROR: Could not read from camera.")
        sys.exit(1)
    frame_h, frame_w = sample_frame.shape[:2]

    tracker = HandTracker(cfg)

    if args.calibrate:
        cfg = run_calibration(cfg, tracker, cap)

    keyboard_ui = VirtualKeyboard(cfg, frame_w, frame_h)
    gesture_mouse = GestureMouse(cfg, SCREEN_W, SCREEN_H, frame_w, frame_h)
    fps_counter = FPSCounter()

    mode = cfg["default_mode"]  # "typing" or "mouse"
    typing_style = args.typing_mode  # "pinch" or "dwell"
    show_landmarks = cfg["show_landmarks"]

    thumbs_up_start = None
    mode_switch_cooldown_until = 0

    print("=" * 60)
    print("AI-Powered Virtual Keyboard running.")
    print("Hold a thumbs-up for 1s to switch modes, or press 'm'.")
    print("Press 'p' to toggle pinch/dwell typing, 'c' to calibrate.")
    print("Press 'q' or ESC to quit.")
    print("=" * 60)

    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)

        hands, results = tracker.process(frame)
        if show_landmarks:
            tracker.draw_landmarks(frame, results)

        index_tip = None
        is_pinching = False
        is_scroll_gesture = False

        if hands:
            hand = hands[0]
            index_tip = hand.index_tip_px()
            is_pinching = hand.pinch_distance() < cfg["pinch_threshold"]

            fingers = hand.fingers_extended()
            is_scroll_gesture = fingers["index"] and fingers["middle"] and not fingers["ring"]

            # Mode switching via thumbs-up hold
            now = time.time()
            if hand.is_thumbs_up():
                if thumbs_up_start is None:
                    thumbs_up_start = now
                elif now - thumbs_up_start >= cfg["mode_switch_hold_time"] and now > mode_switch_cooldown_until:
                    mode = "mouse" if mode == "typing" else "typing"
                    mode_switch_cooldown_until = now + 1.0
                    thumbs_up_start = None
            else:
                thumbs_up_start = None
        else:
            thumbs_up_start = None

        # ---- Mode-specific logic ----
        if mode == "typing":
            highlight_label, progress = None, 0.0
            if typing_style == "dwell":
                typed, progress = keyboard_ui.update_dwell(index_tip)
                if index_tip:
                    key = keyboard_ui.key_at(*index_tip)
                    highlight_label = key.label if key else None
            else:  # pinch style
                typed = keyboard_ui.update_pinch(is_pinching, index_tip)
                if index_tip:
                    key = keyboard_ui.key_at(*index_tip)
                    highlight_label = key.label if key else None

            keyboard_ui.draw(frame, highlight_label=highlight_label, dwell_progress=progress)

        else:  # mouse mode
            gesture_mouse.move(index_tip)
            click_event = gesture_mouse.handle_pinch(is_pinching)
            gesture_mouse.handle_scroll(is_scroll_gesture, index_tip)

            if index_tip:
                cv2.circle(frame, index_tip, 12, (0, 255, 0) if is_pinching else (0, 200, 255), cv2.FILLED)
            cv2.putText(
                frame, "MOUSE MODE", (frame_w - 260, 40), cv2.FONT_HERSHEY_SIMPLEX,
                0.9, (0, 255, 255), 2, cv2.LINE_AA,
            )
            if click_event == "click":
                cv2.putText(frame, "CLICK", (frame_w - 260, 80), cv2.FONT_HERSHEY_SIMPLEX,
                            0.9, (0, 255, 0), 2, cv2.LINE_AA)

        # ---- HUD ----
        if cfg["show_fps"]:
            fps = fps_counter.tick()
            cv2.putText(frame, f"FPS: {fps:.0f}", (frame_w - 150, frame_h - 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)

        mode_text = f"Mode: {mode.upper()}  |  Style: {typing_style}  |  m: switch  p: style  c: calibrate  q: quit"
        cv2.putText(frame, mode_text, (20, frame_h - 20), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (200, 200, 200), 2, cv2.LINE_AA)

        cv2.imshow("AI-Powered Virtual Keyboard", frame)
        key = cv2.waitKey(1) & 0xFF

        if key in (ord("q"), 27):  # q or ESC
            break
        elif key == ord("m"):
            mode = "mouse" if mode == "typing" else "typing"
        elif key == ord("p"):
            typing_style = "dwell" if typing_style == "pinch" else "pinch"
        elif key == ord("l"):
            show_landmarks = not show_landmarks
        elif key == ord("c"):
            cfg = run_calibration(cfg, tracker, cap)
            keyboard_ui.cfg = cfg
            gesture_mouse.cfg = cfg
            gesture_mouse._smoothing = max(1, cfg["mouse_smoothing"])

    save_config(cfg)
    tracker.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
