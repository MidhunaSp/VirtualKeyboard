"""
virtual_keyboard.py
Draws an on-screen QWERTY keyboard and handles the "typing" gesture
logic: either a quick pinch over a key, or dwelling the index
fingertip over a key for a configurable amount of time.
"""

import time

import cv2
from pynput.keyboard import Controller as KeyboardController
from pynput.keyboard import Key

ROWS = [
    list("1234567890"),
    list("QWERTYUIOP"),
    list("ASDFGHJKL") + ["ENTER"],
    ["SHIFT"] + list("ZXCVBNM") + ["BACK"],
    ["SPACE"],
]

SPECIAL_WIDTHS = {
    "ENTER": 1.6,
    "SHIFT": 1.6,
    "BACK": 1.6,
    "SPACE": 6.0,
}

SPECIAL_KEY_ACTIONS = {
    "ENTER": Key.enter,
    "BACK": Key.backspace,
    "SPACE": Key.space,
    "SHIFT": Key.shift,
}


class Key_:
    __slots__ = ("label", "x", "y", "w", "h")

    def __init__(self, label, x, y, w, h):
        self.label = label
        self.x, self.y, self.w, self.h = x, y, w, h

    def contains(self, px, py):
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def center(self):
        return int(self.x + self.w / 2), int(self.y + self.h / 2)


class VirtualKeyboard:
    def __init__(self, cfg, frame_w, frame_h):
        self.cfg = cfg
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.keyboard = KeyboardController()
        self.typed_text = ""
        self.shift_active = False

        self.keys = self._layout_keys()

        # Dwell-typing state
        self._dwell_key = None
        self._dwell_start = None

        # Pinch-typing state
        self._pinch_active = False
        self._pinch_start_time = None
        self._last_typed_time = 0
        self._retype_cooldown = 0.5  # seconds before same key can retrigger

    def _layout_keys(self):
        kw = self.cfg["keyboard_key_width"]
        kh = self.cfg["keyboard_key_height"]
        gap = self.cfg["keyboard_key_gap"]
        top = self.cfg["keyboard_top_offset"]

        keys = []
        for row_idx, row in enumerate(ROWS):
            # compute total row width to center it
            total_w = sum((kw * SPECIAL_WIDTHS.get(k, 1)) + gap for k in row) - gap
            x = (self.frame_w - total_w) / 2
            y = top + row_idx * (kh + gap)
            for label in row:
                w = kw * SPECIAL_WIDTHS.get(label, 1)
                keys.append(Key_(label, x, y, w, kh))
                x += w + gap
        return keys

    def key_at(self, px, py):
        for k in self.keys:
            if k.contains(px, py):
                return k
        return None

    def _emit(self, label):
        """Send the keystroke via pynput and update the local text buffer
        (local buffer is just for on-screen display / demo purposes)."""
        if label in SPECIAL_KEY_ACTIONS:
            if label == "SHIFT":
                self.shift_active = not self.shift_active
                return
            if label == "BACK":
                self.typed_text = self.typed_text[:-1]
                self.keyboard.press(Key.backspace)
                self.keyboard.release(Key.backspace)
                return
            if label == "SPACE":
                self.typed_text += " "
                self.keyboard.press(Key.space)
                self.keyboard.release(Key.space)
                return
            if label == "ENTER":
                self.typed_text += "\n"
                self.keyboard.press(Key.enter)
                self.keyboard.release(Key.enter)
                return
        else:
            ch = label if self.shift_active else label.lower()
            self.typed_text += ch
            self.keyboard.press(ch)
            self.keyboard.release(ch)
            if self.shift_active:
                self.shift_active = False  # one-shot shift like a phone keyboard

    def update_dwell(self, index_tip_px):
        """Call every frame with the current index fingertip pixel
        position (or None if no hand). Returns the label just typed,
        or None. Also returns dwell progress 0-1 for UI feedback."""
        if index_tip_px is None:
            self._dwell_key = None
            self._dwell_start = None
            return None, 0.0

        px, py = index_tip_px
        key = self.key_at(px, py)

        if key is None:
            self._dwell_key = None
            self._dwell_start = None
            return None, 0.0

        if self._dwell_key is not key.label:
            self._dwell_key = key.label
            self._dwell_start = time.time()
            return None, 0.0

        elapsed = time.time() - self._dwell_start
        progress = min(elapsed / self.cfg["dwell_time"], 1.0)

        if elapsed >= self.cfg["dwell_time"]:
            self._emit(key.label)
            self._dwell_start = time.time()  # reset so it doesn't repeat instantly
            self._dwell_key = None
            return key.label, 1.0

        return None, progress

    def update_pinch(self, is_pinching, index_tip_px):
        """Alternative typing mode: pinch (thumb+index touch) while
        index finger hovers a key to type it. Call every frame."""
        if not is_pinching or index_tip_px is None:
            self._pinch_active = False
            return None

        if self._pinch_active:
            return None  # already handled this pinch, wait for release

        now = time.time()
        if now - self._last_typed_time < self._retype_cooldown:
            self._pinch_active = True
            return None

        px, py = index_tip_px
        key = self.key_at(px, py)
        self._pinch_active = True
        if key is not None:
            self._emit(key.label)
            self._last_typed_time = now
            return key.label
        return None

    def draw(self, frame, highlight_label=None, dwell_progress=0.0):
        for k in self.keys:
            is_hot = highlight_label == k.label
            color = (60, 180, 255) if is_hot else (70, 70, 70)
            filled = cv2.FILLED if is_hot else 2
            cv2.rectangle(
                frame,
                (int(k.x), int(k.y)),
                (int(k.x + k.w), int(k.y + k.h)),
                color,
                filled,
            )
            label = k.label
            if label not in SPECIAL_KEY_ACTIONS:
                label = label if self.shift_active else label.lower()
            elif label != "SPACE":
                pass
            else:
                label = ""
            font_scale = 0.5 if len(k.label) > 1 else 0.7
            text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 2)[0]
            tx = int(k.x + (k.w - text_size[0]) / 2)
            ty = int(k.y + (k.h + text_size[1]) / 2)
            cv2.putText(
                frame, label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX,
                font_scale, (255, 255, 255), 2, cv2.LINE_AA,
            )

            # dwell progress ring for the hot key
            if is_hot and 0 < dwell_progress < 1.0:
                cx, cy = k.center()
                radius = int(min(k.w, k.h) / 2) + 6
                angle = int(360 * dwell_progress)
                cv2.ellipse(frame, (cx, cy), (radius, radius), -90, 0, angle, (0, 255, 0), 3)

        # text buffer preview bar
        cv2.rectangle(frame, (20, 20), (self.frame_w - 20, 70), (30, 30, 30), cv2.FILLED)
        preview = self.typed_text[-60:]
        cv2.putText(
            frame, preview, (30, 55), cv2.FONT_HERSHEY_SIMPLEX,
            0.8, (255, 255, 255), 2, cv2.LINE_AA,
        )
