"""এয়ারলাইনের ULD (Unit Load Device) আইডি: যেমন AKE02105BG।

গঠন: ৩ অক্ষরের টাইপ কোড (AKE, AKH, PMC ...) + ৪-৫ অঙ্কের সিরিয়াল + ২ অক্ষরের মালিক (এয়ারলাইনের IATA কোড, যেমন BG)।
ISO 6346 (সমুদ্রপথের কনটেইনার) থেকে আলাদা: ULD আইডিতে check digit নেই, তাই যাচাই শুধু ফরম্যাট, মালিক-কোড ও
(পরে) ফ্লাইটের লোড তালিকার সঙ্গে মিলিয়ে হয়।
"""
from __future__ import annotations

import re

_PATTERN = re.compile(r"^[A-Z]{3}\d{4,5}[A-Z0-9]{2}$")


def normalize(raw: str | None) -> str | None:
    """স্পেস/হাইফেন বাদ দিয়ে বড় হাতের অক্ষরে আনে; ULD আকৃতি না হলে None।"""
    if not raw:
        return None
    s = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    return s if _PATTERN.match(s) else None


def owner(number: str) -> str:
    return number[-2:]


def is_valid(number: str | None, owners: set[str] | None = None) -> bool:
    """ফরম্যাট ঠিক থাকলে এবং (owners দেওয়া থাকলে) মালিক-কোড তাদের একটি হলে true।"""
    n = normalize(number)
    if n is None:
        return False
    return owners is None or owner(n) in owners
