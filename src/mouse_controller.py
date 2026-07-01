"""
mouse_controller.py
Maps index-fingertip position to screen-space mouse movement, with
exponential smoothing, plus pinch-to-click and a simple scroll
gesture (index+middle fingers extended, moving vertically).
"""

import time

from pynput.mouse import Button, Controller as MouseController


class GestureMouse:
    def __init__(self, cfg, screen_w, screen_h, frame_w, frame_h):
        self.cfg = cfg
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.frame_w = frame_w
        self.frame_h = frame_h
        self.mouse = MouseController()

        self._prev_x, self._prev_y = None, None
        self._smoothing = max(1, cfg["mouse_smoothing"])

        self._pinch_active = False
        self._pinch_start_time = None
        self._click_max_duration = cfg["click_max_duration"]

        self._scroll_prev_y = None

        # Active zone: only the central region of the camera frame maps
        # to the full screen, so users don't have to move their hand to
        # the physical edges of the frame.
        margin_x = frame_w * 0.15
        margin_y = frame_h * 0.15
        self.active_box = (margin_x, margin_y, frame_w - margin_x, frame_h - margin_y)

    def _map_to_screen(self, px, py):
        x0, y0, x1, y1 = self.active_box
        nx = (px - x0) / (x1 - x0)
        ny = (py - y0) / (y1 - y0)
        nx = min(max(nx, 0.0), 1.0)
        ny = min(max(ny, 0.0), 1.0)
        return nx * self.screen_w, ny * self.screen_h

    def move(self, index_tip_px):
        if index_tip_px is None:
            self._prev_x, self._prev_y = None, None
            return

        target_x, target_y = self._map_to_screen(*index_tip_px)

        if self._prev_x is None:
            self._prev_x, self._prev_y = target_x, target_y
        else:
            alpha = 1.0 / self._smoothing
            self._prev_x += (target_x - self._prev_x) * alpha
            self._prev_y += (target_y - self._prev_y) * alpha

        self.mouse.position = (int(self._prev_x), int(self._prev_y))

    def handle_pinch(self, is_pinching):
        """Pinch-down then quick release = left click.
        Pinch held longer than click_max_duration = drag (press+hold)."""
        now = time.time()

        if is_pinching and not self._pinch_active:
            self._pinch_active = True
            self._pinch_start_time = now
            return None

        if is_pinching and self._pinch_active:
            held = now - self._pinch_start_time
            if held > self._click_max_duration:
                # Transition into drag if not already pressed
                try:
                    self.mouse.press(Button.left)
                except Exception:
                    pass
            return None

        if not is_pinching and self._pinch_active:
            held = now - self._pinch_start_time
            self._pinch_active = False
            if held <= self._click_max_duration:
                self.mouse.click(Button.left, 1)
                return "click"
            else:
                try:
                    self.mouse.release(Button.left)
                except Exception:
                    pass
                return "drag_end"

        return None

    def handle_scroll(self, is_scroll_gesture, index_tip_px):
        """Scroll when two fingers are extended and moving vertically."""
        if not is_scroll_gesture or index_tip_px is None:
            self._scroll_prev_y = None
            return

        _, py = index_tip_px
        if self._scroll_prev_y is not None:
            dy = py - self._scroll_prev_y
            amount = int(-dy / self.cfg["scroll_sensitivity"])
            if amount != 0:
                self.mouse.scroll(0, amount)
        self._scroll_prev_y = py
