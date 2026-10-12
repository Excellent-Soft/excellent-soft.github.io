"""SQLite স্টোরেজ। প্রোডাকশনে একই স্কিমা PostgreSQL-এ সহজে নেওয়া যায়।"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import DeliveryReport, Observation

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source TEXT NOT NULL, model TEXT NOT NULL, interval_s REAL NOT NULL,
  num_slots INTEGER NOT NULL, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS observations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL REFERENCES runs(id),
  frame_index INTEGER NOT NULL, video_time_s REAL NOT NULL, captured_at TEXT NOT NULL,
  slot INTEGER NOT NULL, container_raw TEXT, container_norm TEXT, check_ok INTEGER NOT NULL,
  door_open INTEGER NOT NULL, unloading INTEGER NOT NULL, people INTEGER NOT NULL,
  confidence TEXT NOT NULL, notes TEXT
);
CREATE TABLE IF NOT EXISTS delivery_reports (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL REFERENCES runs(id),
  slot INTEGER NOT NULL, container_number TEXT, container_valid INTEGER NOT NULL,
  started_at TEXT NOT NULL, ended_at TEXT NOT NULL, duration_s REAL NOT NULL,
  people_peak INTEGER NOT NULL, people_median INTEGER NOT NULL, frames_observed INTEGER NOT NULL,
  needs_review INTEGER NOT NULL, review_reasons TEXT NOT NULL, evidence_path TEXT,
  created_at TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str):
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)

    def start_run(self, source: str, model: str, interval_s: float, num_slots: int) -> int:
        cur = self.conn.execute(
            "INSERT INTO runs(source, model, interval_s, num_slots, created_at) VALUES (?,?,?,?,?)",
            (source, model, interval_s, num_slots, _now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def add_observation(self, run_id: int, o: Observation) -> None:
        self.conn.execute(
            "INSERT INTO observations(run_id, frame_index, video_time_s, captured_at, slot, container_raw,"
            " container_norm, check_ok, door_open, unloading, people, confidence, notes)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, o.frame_index, o.time_s, o.captured_at, o.slot, o.container_raw, o.container_norm,
             int(o.check_ok), int(o.door_open), int(o.unloading), o.people, o.confidence, o.notes),
        )
        self.conn.commit()

    def add_report(self, run_id: int, r: DeliveryReport, evidence_dir: str | None) -> int:
        evidence_path = None
        if r.evidence_jpeg and evidence_dir:
            Path(evidence_dir).mkdir(parents=True, exist_ok=True)
            name = f"run{run_id}_slot{r.slot}_{r.container_number or 'unknown'}_{int(r.duration_s)}s.jpg"
            evidence_path = str(Path(evidence_dir) / name)
            Path(evidence_path).write_bytes(r.evidence_jpeg)
        cur = self.conn.execute(
            "INSERT INTO delivery_reports(run_id, slot, container_number, container_valid, started_at, ended_at,"
            " duration_s, people_peak, people_median, frames_observed, needs_review, review_reasons,"
            " evidence_path, created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (run_id, r.slot, r.container_number, int(r.container_valid), r.started_at, r.ended_at,
             r.duration_s, r.people_peak, r.people_median, r.frames_observed, int(r.needs_review),
             json.dumps(r.review_reasons, ensure_ascii=False), evidence_path, _now()),
        )
        self.conn.commit()
        return cur.lastrowid

    def reports(self, run_id: int | None = None) -> list[sqlite3.Row]:
        q, args = "SELECT * FROM delivery_reports", ()
        if run_id is not None:
            q, args = q + " WHERE run_id=?", (run_id,)
        return self.conn.execute(q + " ORDER BY started_at, slot", args).fetchall()

    def close(self) -> None:
        self.conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
