from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from . import iso6346, uld
from .aggregator import Aggregator
from .analyzer import Analyzer
from .db import Database
from .frames import sample_frames
from .models import DeliveryReport, Observation

log = logging.getLogger(__name__)


def run(
    source: str,
    analyzer: Analyzer,
    db: Database,
    run_id: int,
    *,
    interval_s: float = 3.0,
    start_time: datetime | None = None,
    start_s: float = 0.0,
    end_s: float | None = None,
    max_frames: int | None = None,
    evidence_dir: str | None = "evidence",
    aggregator: Aggregator | None = None,
    id_scheme: str = "uld",
    owners: set[str] | None = None,
) -> list[DeliveryReport]:
    """ভিডিও (বা স্ট্রিম) -> ফ্রেম -> বিশ্লেষণ -> যাচাই -> সেশন -> ডাটাবেজ।

    start_time হলো ভিডিওর শুরুর আসল (ঘড়ির) সময়; না দিলে এখনকার সময় ধরা হয়।
    """
    base = start_time or datetime.now(timezone.utc)
    agg = aggregator or Aggregator()
    saved: list[DeliveryReport] = []

    def store(reports: list[DeliveryReport]) -> None:
        for r in reports:
            db.add_report(run_id, r, evidence_dir)
            saved.append(r)
            log.info("রিপোর্ট: slot %s %s (%s -> %s, মানুষ %s)", r.slot, r.container_number,
                     r.started_at, r.ended_at, r.people_peak)

    for frame in sample_frames(source, interval_s, start_s, end_s, max_frames):
        analysis = analyzer.analyze(frame.jpeg)
        if analysis is None:
            log.warning("ফ্রেম %s বিশ্লেষণ হয়নি, বাদ", frame.index)
            continue
        captured_at = (base + timedelta(seconds=frame.time_s)).isoformat(timespec="seconds")
        seen: set[int] = set()
        for s in analysis.slots:
            if s.slot in seen:  # একই slot দুইবার এলে প্রথমটি রাখা হয়
                continue
            seen.add(s.slot)
            if id_scheme == "iso6346":
                norm = iso6346.normalize(s.container_number_raw)
                ok = bool(norm) and iso6346.is_valid(norm)
            else:  # "uld": বিমানের কনটেইনার (ফরম্যাট + মালিক-কোড যাচাই, check digit নেই)
                norm = uld.normalize(s.container_number_raw)
                ok = bool(norm) and uld.is_valid(norm, owners)
            obs = Observation(
                frame_index=frame.index, time_s=frame.time_s, captured_at=captured_at, slot=s.slot,
                container_raw=s.container_number_raw, container_norm=norm,
                check_ok=ok,
                door_open=s.door_open, unloading=s.baggage_being_unloaded,
                people=max(0, s.people_count), confidence=s.confidence, notes=s.notes,
            )
            db.add_observation(run_id, obs)
            store(agg.feed(obs, frame.jpeg))
    store(agg.flush())
    return saved
