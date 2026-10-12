"""ভিডিও ফাইল (বা পরে RTSP URL) থেকে নির্দিষ্ট বিরতিতে ফ্রেম বের করা।"""
from __future__ import annotations

from collections.abc import Iterator

import cv2

from .models import Frame

MAX_SIDE = 1568  # Claude-এর জন্য বড় ছবি এর বেশি হলে ছোট করে দেওয়া হয়


def video_info(source: str) -> tuple[float, float]:
    """(fps, দৈর্ঘ্য সেকেন্ডে) ফেরত দেয়। দৈর্ঘ্য অজানা (লাইভ) হলে 0।"""
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise FileNotFoundError(f"ভিডিও খোলা যায়নি: {source}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
    cap.release()
    return fps, (count / fps if count > 0 else 0.0)


def sample_frames(
    source: str,
    interval_s: float = 3.0,
    start_s: float = 0.0,
    end_s: float | None = None,
    max_frames: int | None = None,
) -> Iterator[Frame]:
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise FileNotFoundError(f"ভিডিও খোলা যায়নি: {source}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, round(interval_s * fps))
    first = round(start_s * fps)
    if first:
        cap.set(cv2.CAP_PROP_POS_FRAMES, first)
    i, emitted = first, 0
    try:
        while True:
            t = i / fps
            if end_s is not None and t > end_s:
                return
            ok, img = cap.read()
            if not ok:
                return
            yield Frame(index=i, time_s=t, jpeg=_encode(img))
            emitted += 1
            if max_frames is not None and emitted >= max_frames:
                return
            for _ in range(step - 1):  # মাঝের ফ্রেমগুলো ডিকোড না করে বাদ
                if not cap.grab():
                    return
            i += step
    finally:
        cap.release()


def _encode(img) -> bytes:
    h, w = img.shape[:2]
    scale = MAX_SIDE / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    if not ok:
        raise RuntimeError("JPEG এনকোড ব্যর্থ")
    return buf.tobytes()
