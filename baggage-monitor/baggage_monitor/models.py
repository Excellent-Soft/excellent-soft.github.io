from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, Field


class SlotObservation(BaseModel):
    """একটি ফ্রেমে একটি কনটেইনার-স্লটের পর্যবেক্ষণ (Claude-এর structured output)।"""

    slot: int = Field(description="বাঁ থেকে ডানে কনটেইনারের ক্রম, ১ থেকে শুরু")
    container_number_raw: str | None = Field(
        description="কনটেইনারের গায়ে স্পষ্ট পড়া যাচ্ছে এমন আইডি হুবহু (যেমন AKE02105BG); পড়া না গেলে null"
    )
    door_open: bool = Field(description="কনটেইনারের দরজা খোলা কিনা")
    baggage_being_unloaded: bool = Field(
        description="এই ফ্রেমে এই কনটেইনার থেকে এখন ব্যাগ নামানো/বহন হচ্ছে কিনা"
    )
    people_count: int = Field(description="এই কনটেইনারের কাজে যুক্ত দৃশ্যমান মানুষের সংখ্যা")
    confidence: Literal["low", "medium", "high"]
    notes: str = Field(description="এক লাইনে সংক্ষিপ্ত মন্তব্য (ইংরেজি বা বাংলা)")


class FrameAnalysis(BaseModel):
    slots: list[SlotObservation]
    scene_summary: str = Field(description="পুরো দৃশ্যের এক বাক্যের বিবরণ")


@dataclass
class Frame:
    index: int
    time_s: float  # ভিডিওর ভেতরের সময় (সেকেন্ড)
    jpeg: bytes


@dataclass
class Observation:
    """একটি ফ্রেম x একটি স্লট; ডাটাবেজে raw লগ হিসেবে যায়।"""

    frame_index: int
    time_s: float
    captured_at: str  # ISO-8601 (ক্যাপচারের আসল সময়)
    slot: int
    container_raw: str | None
    container_norm: str | None
    check_ok: bool
    door_open: bool
    unloading: bool
    people: int
    confidence: str
    notes: str


@dataclass
class DeliveryReport:
    slot: int
    container_number: str | None
    container_valid: bool
    started_at: str
    ended_at: str
    duration_s: float
    people_peak: int
    people_median: int
    frames_observed: int
    needs_review: bool
    review_reasons: list[str] = field(default_factory=list)
    evidence_jpeg: bytes | None = None  # সবচেয়ে ভালো নম্বর-পড়া ফ্রেম
