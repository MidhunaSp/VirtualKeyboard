"""
hand_tracker.py
Thin wrapper around MediaPipe Hands that exposes just what the rest
of the app needs: landmark positions, pinch distance, and a couple
of derived gestures (pinch, thumbs-up).
"""

import math
import time

import cv2
import mediapipe as mp


# Landmark indices we care about (see MediaPipe hand landmark diagram)
THUMB_TIP = 4
INDEX_TIP = 8
INDEX_MCP = 5
MIDDLE_TIP = 12
RING_TIP = 16
PINKY_TIP = 20
WRIST = 0


class Hand:
    """Snapshot of a single tracked hand for one frame."""

    def __init__(self, landmarks, handedness, frame_w, frame_h):
        self.landmarks = landmarks  # list of (x, y, z) normalized
        self.handedness = handedness
        self.frame_w = frame_w
        self.frame_h = frame_h

    def px(self, idx):
        """Pixel coordinates for a landmark index."""
        x, y, _ = self.landmarks[idx]
        return int(x * self.frame_w), int(y * self.frame_h)

    def norm(self, idx):
        """Normalized (0-1) coordinates for a landmark index."""
        x, y, _ = self.landmarks[idx]
        return x, y

    def hand_size(self):
        """Rough scale reference: wrist-to-middle-MCP distance."""
        wx, wy = self.norm(WRIST)
        mx, my = self.norm(INDEX_MCP)
        return math.hypot(mx - wx, my - wy) + 1e-6

    def pinch_distance(self):
        """Normalized distance between thumb tip and index tip,
        scaled by hand size so it's roughly camera-distance invariant."""
        tx, ty = self.norm(THUMB_TIP)
        ix, iy = self.norm(INDEX_TIP)
        raw = math.hypot(tx - ix, ty - iy)
        return raw / self.hand_size() * 0.3  # empirical scale factor

    def index_tip_px(self):
        return self.px(INDEX_TIP)

    def is_thumbs_up(self):
        """Very rough thumbs-up heuristic: thumb tip well above the
        rest of the fingers' tips (in image space, lower y = higher)."""
        thumb_y = self.norm(THUMB_TIP)[1]
        other_ys = [
            self.norm(INDEX_TIP)[1],
            self.norm(MIDDLE_TIP)[1],
            self.norm(RING_TIP)[1],
            self.norm(PINKY_TIP)[1],
        ]
        return thumb_y < min(other_ys) - 0.08

    def fingers_extended(self):
        """Return dict of which fingers are extended, using tip-vs-pip
        y comparisons. Useful for future gesture expansion."""
        tips = [INDEX_TIP, MIDDLE_TIP, RING_TIP, PINKY_TIP]
        pips = [6, 10, 14, 18]
        result = {}
        names = ["index", "middle", "ring", "pinky"]
        for name, tip, pip in zip(names, tips, pips):
            result[name] = self.norm(tip)[1] < self.norm(pip)[1]
        return result


class HandTracker:
    def __init__(self, cfg):
        self.cfg = cfg
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            max_num_hands=cfg["max_num_hands"],
            min_detection_confidence=cfg["detection_confidence"],
            min_tracking_confidence=cfg["tracking_confidence"],
        )
        self.mp_draw = mp.solutions.drawing_utils
        self.mp_styles = mp.solutions.drawing_styles

    def process(self, frame_bgr):
        """Run detection on a BGR frame. Returns (hands, results)."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self.hands.process(rgb)
        rgb.flags.writeable = True

        h, w = frame_bgr.shape[:2]
        hands = []
        if results.multi_hand_landmarks:
            for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
                pts = [(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
                handedness = "Right"
                if results.multi_handedness:
                    handedness = results.multi_handedness[i].classification[0].label
                hands.append(Hand(pts, handedness, w, h))
        return hands, results

    def draw_landmarks(self, frame_bgr, results):
        if not results.multi_hand_landmarks:
            return
        for hand_landmarks in results.multi_hand_landmarks:
            self.mp_draw.draw_landmarks(
                frame_bgr,
                hand_landmarks,
                self.mp_hands.HAND_CONNECTIONS,
                self.mp_styles.get_default_hand_landmarks_style(),
                self.mp_styles.get_default_hand_connections_style(),
            )

    def close(self):
        self.hands.close()


class FPSCounter:
    def __init__(self, smoothing=0.9):
        self.smoothing = smoothing
        self.fps = 0.0
        self._last = time.time()

    def tick(self):
        now = time.time()
        dt = now - self._last
        self._last = now
        if dt > 0:
            instant = 1.0 / dt
            self.fps = self.smoothing * self.fps + (1 - self.smoothing) * instant
        return self.fps
