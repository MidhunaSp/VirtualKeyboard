"""
config.py
Central place for all tunable parameters. Values here are defaults;
the calibration module can override them at runtime and persist
changes to calibration.json.
"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "calibration.json")

DEFAULTS = {
    # --- Camera ---
    "camera_index": 0,
    "frame_width": 1280,
    "frame_height": 720,

    # --- Hand tracking ---
    "max_num_hands": 1,
    "detection_confidence": 0.7,
    "tracking_confidence": 0.6,

    # --- Gesture thresholds ---
    # Distance (normalized 0-1, roughly relative to hand size) between
    # thumb tip and index tip below which we consider it a "pinch".
    "pinch_threshold": 0.045,

    # How long (seconds) the pinch must be held to register as a click
    # vs. treated as a drag/hold.
    "click_max_duration": 0.35,

    # --- Dwell typing ---
    # Time in seconds the index fingertip must hover over a key
    # before it is "typed" (used as an alternative to pinch-typing).
    "dwell_time": 0.8,

    # Radius (pixels) within which the finger must stay to keep
    # dwelling on the same key.
    "dwell_radius": 25,

    # --- Mouse control ---
    "mouse_smoothing": 5,       # higher = smoother but laggier
    "mouse_sensitivity": 1.6,   # multiplier mapping hand movement to screen movement
    "scroll_sensitivity": 20,

    # --- Modes ---
    # "typing" or "mouse" -- switched with a thumbs-up gesture hold
    "default_mode": "typing",
    "mode_switch_hold_time": 1.0,

    # --- UI ---
    "keyboard_key_width": 60,
    "keyboard_key_height": 60,
    "keyboard_key_gap": 8,
    "keyboard_top_offset": 400,
    "show_landmarks": True,
    "show_fps": True,
}


def load_config():
    """Load calibration.json if present, falling back to DEFAULTS."""
    cfg = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                saved = json.load(f)
            cfg.update(saved)
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save_config(cfg):
    """Persist the given config dict to calibration.json."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
