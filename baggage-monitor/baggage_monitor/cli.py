from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime, timezone

from .analyzer import ClaudeAnalyzer, DEFAULT_MODEL, MockAnalyzer
from .db import Database
from .frames import video_info
from .pipeline import run


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="baggage_monitor", description="ব্যাগেজ ডেলিভারি ভিডিও বিশ্লেষণ")
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze", help="ভিডিও বিশ্লেষণ করে ডাটাবেজে রিপোর্ট সেভ")
    a.add_argument("video")
    a.add_argument("--db", default="baggage.db")
    a.add_argument("--slots", type=int, default=4, help="ফ্রেমে কনটেইনারের সংখ্যা")
    a.add_argument("--interval", type=float, default=3.0, help="কত সেকেন্ড পরপর একটি ফ্রেম")
    a.add_argument("--start", type=float, default=0.0, help="ভিডিওর কত সেকেন্ড থেকে শুরু")
    a.add_argument("--end", type=float, default=None)
    a.add_argument("--max-frames", type=int, default=200, help="খরচ সীমিত রাখার নিরাপত্তা-সীমা")
    a.add_argument("--start-time", help="ভিডিওর শুরুর আসল সময় ISO-8601, যেমন 2026-10-12T09:30:00+06:00")
    a.add_argument("--model", default=None, help=f"ডিফল্ট {DEFAULT_MODEL} (বা CLAUDE_MODEL env)")
    a.add_argument("--no-fallback", action="store_true", help="server-side refusal fallback বন্ধ")
    a.add_argument("--evidence-dir", default="evidence")
    a.add_argument("--mock", action="store_true", help="Claude ছাড়া বানানো ডেটায় পাইপলাইন পরীক্ষা (API খরচ নেই)")

    r = sub.add_parser("report", help="সেভ করা রিপোর্ট দেখা")
    r.add_argument("--db", default="baggage.db")
    r.add_argument("--run", type=int, default=None)
    r.add_argument("--json", action="store_true")

    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if args.cmd == "report":
        return _report(args)

    fps, duration = video_info(args.video)
    end = min(args.end, duration) if args.end and duration else (args.end or duration or None)
    n_frames = int(((end or 0) - args.start) / args.interval) + 1 if end else args.max_frames
    n_frames = min(n_frames, args.max_frames)
    start_time = datetime.fromisoformat(args.start_time) if args.start_time else datetime.now(timezone.utc)

    if args.mock:
        analyzer, model = MockAnalyzer(args.slots), "mock"
    else:
        analyzer = ClaudeAnalyzer(args.slots, args.model, fallback=not args.no_fallback)
        model = analyzer.model
    print(f"ভিডিও {duration:.0f}s, fps {fps:.0f}; মডেল {model}; প্রায় {n_frames}টি ফ্রেম পাঠানো হবে "
          f"(সীমা {args.max_frames})", file=sys.stderr)

    db = Database(args.db)
    run_id = db.start_run(args.video, model, args.interval, args.slots)
    reports = run(args.video, analyzer, db, run_id, interval_s=args.interval, start_time=start_time,
                  start_s=args.start, end_s=args.end, max_frames=args.max_frames,
                  evidence_dir=args.evidence_dir)
    if hasattr(analyzer, "input_tokens"):
        print(f"টোকেন: ইনপুট {analyzer.input_tokens}, আউটপুট {analyzer.output_tokens}", file=sys.stderr)
    print(f"রান #{run_id}: {len(reports)}টি ডেলিভারি রিপোর্ট সেভ হয়েছে -> {args.db}", file=sys.stderr)
    _print_table(db.reports(run_id))
    db.close()
    return 0


def _report(args) -> int:
    db = Database(args.db)
    rows = db.reports(args.run)
    if args.json:
        print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
    else:
        _print_table(rows)
    db.close()
    return 0


def _print_table(rows) -> None:
    if not rows:
        print("কোনো ডেলিভারি রিপোর্ট নেই।")
        return
    print(f"{'slot':<5}{'কনটেইনার':<14}{'শুরু':<27}{'শেষ':<27}{'মিনিট':<7}{'মানুষ(max/med)':<16}রিভিউ")
    for r in rows:
        mark = "✔" if r["container_valid"] else "?"
        review = "হ্যাঁ: " + "; ".join(json.loads(r["review_reasons"])) if r["needs_review"] else "না"
        print(f"{r['slot']:<5}{(r['container_number'] or '-') + mark:<14}{r['started_at']:<27}"
              f"{r['ended_at']:<27}{r['duration_s'] / 60:<7.1f}{r['people_peak']}/{r['people_median']:<13}{review}")
