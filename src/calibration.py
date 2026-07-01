"""
calibration.py
A small interactive OpenCV screen that lets the user tune pinch
sensitivity, dwell speed, and mouse smoothing with trackbars before
launching the main app. Saves results to calibration.json via
config.save_config().
"""

import cv2

from config import save_config


def _nothing(_):
    pass


def run_calibration(cfg, tracker, cap):
    """Show a live camera feed with trackbars for the key thresholds.
    Press 's' to save and continue, 'q' to quit without saving,
    or 'd' to reset to defaults for this session."""
    window = "Calibration - s: save & continue | q: quit | d: defaults"
    cv2.namedWindow(window)

    # Trackbars use integers, so we scale float configs up.
    cv2.createTrackbar("Pinch x1000", window, int(cfg["pinch_threshold"] * 1000), 150, _nothing)
    cv2.createTrackbar("Dwell x10 (s)", window, int(cfg["dwell_time"] * 10), 30, _nothing)
    cv2.createTrackbar("Mouse Smoothing", window, cfg["mouse_smoothing"], 20, _nothing)
    cv2.createTrackbar("Mouse Sensitivity x10", window, int(cfg["mouse_sensitivity"] * 10), 40, _nothing)

    while True:
        ok, frame = cap.read()
        if not ok:
            continue
        frame = cv2.flip(frame, 1)

        pinch_val = cv2.getTrackbarPos("Pinch x1000", window) / 1000.0
        dwell_val = cv2.getTrackbarPos("Dwell x10 (s)", window) / 10.0
        smoothing_val = max(1, cv2.getTrackbarPos("Mouse Smoothing", window))
        sensitivity_val = cv2.getTrackbarPos("Mouse Sensitivity x10", window) / 10.0

        hands, results = tracker.process(frame)
        tracker.draw_landmarks(frame, results)

        status_lines = [
            f"Pinch threshold: {pinch_val:.3f}",
            f"Dwell time: {dwell_val:.1f}s",
            f"Mouse smoothing: {smoothing_val}",
            f"Mouse sensitivity: {sensitivity_val:.1f}",
        ]

        if hands:
            hand = hands[0]
            dist = hand.pinch_distance()
            is_pinch = dist < pinch_val
            status_lines.append(f"Live pinch distance: {dist:.3f} {'(PINCHING)' if is_pinch else ''}")

            tx, ty = hand.px(4)
            ix, iy = hand.px(8)
            color = (0, 255, 0) if is_pinch else (0, 0, 255)
            cv2.line(frame, (tx, ty), (ix, iy), color, 2)
            cv2.circle(frame, (tx, ty), 8, color, cv2.FILLED)
            cv2.circle(frame, (ix, iy), 8, color, cv2.FILLED)

        for i, line in enumerate(status_lines):
            cv2.putText(
                frame, line, (20, 100 + i * 30), cv2.FONT_HERSHEY_SIMPLEX,
                0.65, (255, 255, 0), 2, cv2.LINE_AA,
            )

        cv2.putText(
            frame, "Pinch thumb+index to test | s=save q=quit d=defaults",
            (20, frame.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX,
            0.6, (200, 200, 200), 2, cv2.LINE_AA,
        )

        cv2.imshow(window, frame)
        key = cv2.waitKey(1) & 0xFF

        if key == ord("s"):
            cfg["pinch_threshold"] = pinch_val
            cfg["dwell_time"] = dwell_val
            cfg["mouse_smoothing"] = smoothing_val
            cfg["mouse_sensitivity"] = sensitivity_val
            save_config(cfg)
            break
        elif key == ord("q"):
            break
        elif key == ord("d"):
            from config import DEFAULTS
            cv2.setTrackbarPos("Pinch x1000", window, int(DEFAULTS["pinch_threshold"] * 1000))
            cv2.setTrackbarPos("Dwell x10 (s)", window, int(DEFAULTS["dwell_time"] * 10))
            cv2.setTrackbarPos("Mouse Smoothing", window, DEFAULTS["mouse_smoothing"])
            cv2.setTrackbarPos("Mouse Sensitivity x10", window, int(DEFAULTS["mouse_sensitivity"] * 10))

    cv2.destroyWindow(window)
    return cfg
