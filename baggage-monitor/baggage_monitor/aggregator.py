"""ফ্রেম-ভিত্তিক পর্যবেক্ষণ জুড়ে প্রতিটি স্লটের ডেলিভারি সেশন তৈরি (শুরু/শেষ/মানুষ/কনটেইনার নম্বর)।

একটি ফ্রেমের ওপর ভরসা না করে কয়েকটি ধারাবাহিক ফ্রেম মিলিয়ে সিদ্ধান্ত নেওয়া হয়, তাই এক ফ্রেমের ভুল রিপোর্ট বদলায় না।
"""
from __future__ import annotations

import statistics
from collections import Counter
from dataclasses import dataclass, field

from .models import DeliveryReport, Observation


@dataclass
class _Session:
    started_at: str
    first_time_s: float
    last_active_at: str
    last_active_time_s: float
    valid_votes: Counter = field(default_factory=Counter)
    invalid_votes: Counter = field(default_factory=Counter)
    people: list[int] = field(default_factory=list)
    low_conf: int = 0
    frames: int = 0
    best_jpeg: bytes | None = None
    best_score: int = -1


@dataclass
class _SlotState:
    run_active: int = 0  # পরপর কতগুলো active ফ্রেম (শুরুর আগে)
    run_inactive: int = 0  # পরপর কতগুলো inactive ফ্রেম (শেষের আগে)
    pending: list[tuple[Observation, bytes | None]] = field(default_factory=list)
    session: _Session | None = None


class Aggregator:
    def __init__(self, start_frames: int = 2, end_frames: int = 3):
        self.start_frames = start_frames  # শুরু ধরতে পরপর এতগুলো active ফ্রেম লাগবে
        self.end_frames = end_frames  # শেষ ধরতে পরপর এতগুলো inactive ফ্রেম লাগবে
        self._slots: dict[int, _SlotState] = {}

    def feed(self, obs: Observation, jpeg: bytes | None = None) -> list[DeliveryReport]:
        """একটি পর্যবেক্ষণ নেয়; কোনো সেশন শেষ হলে তার রিপোর্ট ফেরত দেয়।"""
        st = self._slots.setdefault(obs.slot, _SlotState())
        done: list[DeliveryReport] = []

        if st.session is None:
            if obs.unloading:
                st.pending.append((obs, jpeg))
                if len(st.pending) >= self.start_frames:
                    first = st.pending[0][0]
                    st.session = _Session(first.captured_at, first.time_s, first.captured_at, first.time_s)
                    for o, j in st.pending:
                        self._add(st.session, o, j)
                    st.pending.clear()
                    st.run_inactive = 0
            else:
                st.pending.clear()
            return done

        # চলমান সেশন
        if obs.unloading:
            st.run_inactive = 0
            self._add(st.session, obs, jpeg)
        else:
            st.run_inactive += 1
            # কনটেইনার নম্বর শুধু নিষ্ক্রিয় অবস্থাতেও পড়া গেলে ভোট হিসেবে নেওয়া হয়
            self._vote(st.session, obs, jpeg)
            if st.run_inactive >= self.end_frames:
                done.append(self._close(obs.slot, st.session))
                st.session = None
        return done

    def flush(self) -> list[DeliveryReport]:
        """ভিডিও শেষ: চলমান সেশনগুলো বন্ধ করে রিপোর্ট দেয়।"""
        out = []
        for slot, st in self._slots.items():
            if st.session is not None:
                out.append(self._close(slot, st.session))
                st.session = None
        return out

    # ---- ভেতরের সহায়ক ----
    def _add(self, s: _Session, o: Observation, jpeg: bytes | None) -> None:
        s.last_active_at, s.last_active_time_s = o.captured_at, o.time_s
        s.people.append(o.people)
        s.frames += 1
        if o.confidence == "low":
            s.low_conf += 1
        self._vote(s, o, jpeg)

    @staticmethod
    def _vote(s: _Session, o: Observation, jpeg: bytes | None) -> None:
        if not o.container_norm:
            return
        if o.check_ok:
            s.valid_votes[o.container_norm] += 1
            score = {"low": 1, "medium": 2, "high": 3}.get(o.confidence, 1)
            if jpeg is not None and score > s.best_score:
                s.best_jpeg, s.best_score = jpeg, score
        else:
            s.invalid_votes[o.container_norm] += 1

    def _close(self, slot: int, s: _Session) -> DeliveryReport:
        reasons: list[str] = []
        if s.valid_votes:
            number, votes = s.valid_votes.most_common(1)[0]
            valid = True
            if len(s.valid_votes) > 1:
                reasons.append("একাধিক ভিন্ন বৈধ কনটেইনার নম্বর পড়া হয়েছে: " + ", ".join(s.valid_votes))
            if votes < 2:
                reasons.append("নম্বর মাত্র একটি ফ্রেমে পড়া গেছে")
        elif s.invalid_votes:
            number, _ = s.invalid_votes.most_common(1)[0]
            valid = False
            reasons.append("পড়া নম্বরের ফরম্যাট বা মালিক-কোড মেলেনি (পড়ায় ভুল হতে পারে)")
        else:
            number, valid = None, False
            reasons.append("কনটেইনার নম্বর পড়া যায়নি")
        if s.frames and s.low_conf / s.frames > 0.4:
            reasons.append("অনেক ফ্রেমে confidence কম")
        if s.frames < 3:
            reasons.append("খুব অল্প ফ্রেমের ওপর ভিত্তি করা রিপোর্ট")
        # মানুষের সংখ্যা অনুমান-ভিত্তিক: সংখ্যা খুব ওঠানামা করলে রিভিউ
        if len(s.people) >= 3 and statistics.pstdev(s.people) > 1.5:
            reasons.append("মানুষের সংখ্যা ফ্রেমভেদে অনেক বদলেছে")
        return DeliveryReport(
            slot=slot,
            container_number=number,
            container_valid=valid,
            started_at=s.started_at,
            ended_at=s.last_active_at,
            duration_s=round(s.last_active_time_s - s.first_time_s, 1),
            people_peak=max(s.people) if s.people else 0,
            people_median=round(statistics.median(s.people)) if s.people else 0,
            frames_observed=s.frames,
            needs_review=bool(reasons),
            review_reasons=reasons,
            evidence_jpeg=s.best_jpeg,
        )
