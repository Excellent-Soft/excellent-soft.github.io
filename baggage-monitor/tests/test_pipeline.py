import cv2
import numpy as np

from baggage_monitor.analyzer import MockAnalyzer
from baggage_monitor.db import Database
from baggage_monitor.frames import sample_frames
from baggage_monitor.pipeline import run


def make_video(path, seconds=40, fps=10):
    w = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (320, 240))
    for i in range(seconds * fps):
        w.write(np.full((240, 320, 3), i % 255, np.uint8))
    w.release()


def test_sampling_interval(tmp_path):
    v = tmp_path / "v.mp4"
    make_video(v)
    frames = list(sample_frames(str(v), interval_s=5))
    assert [round(f.time_s) for f in frames] == [0, 5, 10, 15, 20, 25, 30, 35]
    assert frames[0].jpeg[:2] == b"\xff\xd8"


def test_end_to_end_with_mock(tmp_path):
    v = tmp_path / "v.mp4"
    make_video(v)
    db = Database(str(tmp_path / "t.db"))
    rid = db.start_run(str(v), "mock", 3, 4)
    reports = run(str(v), MockAnalyzer(4), db, rid, interval_s=3, evidence_dir=str(tmp_path / "ev"))
    rows = db.reports(rid)
    assert len(rows) == len(reports) == 2  # mock-এ slot 1 ও 3 সক্রিয়
    assert {r["slot"] for r in rows} == {1, 3}
    assert all(r["people_peak"] > 0 for r in rows)
    assert (tmp_path / "ev").exists()
