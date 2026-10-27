"""Scene change detection via frame differencing (OpenCV)."""
import cv2, numpy as np, json

def detect_scene_changes(video_path, threshold=25.0, sample_every=3):
    """Return list of (time, score) where frame diff exceeds threshold."""
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    prev = None
    results = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % sample_every != 0:
            idx += 1
            continue
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (160, 90))
        if prev is not None:
            diff = float(np.mean(cv2.absdiff(gray, prev)))
            if diff >= threshold:
                results.append({"time": round(idx / fps, 3), "score": round(diff, 2)})
        prev = gray
        idx += 1
    cap.release()
    return results
