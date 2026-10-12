"""ফ্রেম বিশ্লেষক: Claude vision (প্রোডাকশন) এবং একটি mock (শুধু পাইপলাইন টেস্টের জন্য)।"""
from __future__ import annotations

import base64
import logging
import os
from typing import Protocol

import anthropic

from .models import FrameAnalysis

log = logging.getLogger(__name__)

# মডেল বদলাতে: CLAUDE_MODEL=claude-haiku-5-5 (সস্তা/দ্রুত) বা claude-sonnet-5-5
DEFAULT_MODEL = "claude-opus-5-5"


class Analyzer(Protocol):
    def analyze(self, jpeg: bytes) -> FrameAnalysis | None: ...


def build_prompt(num_slots: int) -> str:
    return f"""এটি একটি স্থির ক্যামেরার ফ্রেম। ক্যামেরায় {num_slots}টি কনটেইনার থেকে ব্যাগেজ নামানোর কাজ দেখা যায়।
কনটেইনারগুলোকে ফ্রেমে বাঁ থেকে ডানে slot 1 থেকে slot {num_slots} ধরো। প্রতিটি slot-এর জন্য ঠিক একটি এন্ট্রি দাও
(কনটেইনার দেখা না গেলেও), এবং ফ্রেমে যা দেখছ শুধু তা-ই রিপোর্ট করো।

নিয়ম:
- container_number_raw: কনটেইনারের গায়ে লেখা নম্বর (ISO 6346: ৪টি অক্ষর + ৬টি অঙ্ক + ১টি check digit, যেমন CSQU 305438 3)
  যেটুকু স্পষ্ট পড়া যাচ্ছে হুবহু লেখো। অস্পষ্ট বা আংশিক দেখা গেলে অনুমান করে পূর্ণ করবে না; null দাও।
- baggage_being_unloaded: true শুধু তখনই যখন ওই কনটেইনার থেকে কেউ ব্যাগ ধরে/বহন করছে বা কনভেয়ারে তুলছে। দরজা খোলা অথচ কেউ কাজ করছে না হলে false।
- people_count: যারা স্পষ্টভাবে ওই কনটেইনারের কাজে যুক্ত শুধু তাদের গোনো; পথচারী বা দূরের মানুষ বাদ।
- confidence: ছবি অস্পষ্ট, আড়াল বা কম আলো হলে low।
"""


class ClaudeAnalyzer:
    def __init__(self, num_slots: int, model: str | None = None, fallback: bool = True):
        self.client = anthropic.Anthropic()  # ANTHROPIC_API_KEY বা `ant auth login` থেকে
        self.model = model or os.environ.get("CLAUDE_MODEL", DEFAULT_MODEL)
        self.prompt = build_prompt(num_slots)
        self.fallback = fallback
        self.input_tokens = 0
        self.output_tokens = 0

    def analyze(self, jpeg: bytes) -> FrameAnalysis | None:
        extra = {}
        if self.fallback:
            # নীতিগত কারণে রিফিউজ হলে সার্ভার নিজেই fallback মডেলে আবার চালায়
            extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
        try:
            resp = self.client.beta.messages.parse(
                model=self.model,
                max_tokens=8000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64.standard_b64encode(jpeg).decode(),
                                },
                            },
                            {"type": "text", "text": self.prompt},
                        ],
                    }
                ],
                output_format=FrameAnalysis,
                **extra,
            )
        except anthropic.APIStatusError as e:
            log.error("Claude API ত্রুটি %s: %s", e.status_code, e.message)
            return None
        except anthropic.APIConnectionError as e:
            log.error("নেটওয়ার্ক ত্রুটি: %s", e)
            return None
        self.input_tokens += resp.usage.input_tokens
        self.output_tokens += resp.usage.output_tokens
        if resp.stop_reason == "refusal":
            log.warning("ফ্রেমটি Claude রিফিউজ করেছে, বাদ দেওয়া হলো")
            return None
        return resp.parsed_output


class MockAnalyzer:
    """শুধু পাইপলাইন পরীক্ষার জন্য: ফ্রেমের ক্রম অনুযায়ী বানানো ডেটা দেয়। আসল বিশ্লেষণ নয়।"""

    def __init__(self, num_slots: int):
        self.num_slots = num_slots
        self.n = 0

    def analyze(self, jpeg: bytes) -> FrameAnalysis:
        from .models import SlotObservation

        n, self.n = self.n, self.n + 1
        numbers = ["CSQU3054383", "MSKU9070323", None, "TCNU1234565"]
        slots = []
        for s in range(1, self.num_slots + 1):
            active = 2 <= n <= 8 and s % 2 == 1
            slots.append(
                SlotObservation(
                    slot=s,
                    container_number_raw=numbers[(s - 1) % 4] if n >= 1 else None,
                    door_open=n >= 1,
                    baggage_being_unloaded=active,
                    people_count=(2 + s % 3) if active else 0,
                    confidence="high",
                    notes="mock",
                )
            )
        return FrameAnalysis(slots=slots, scene_summary="mock scene")
