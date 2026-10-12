"""ISO 6346 কনটেইনার নম্বর (যেমন CSQU3054383) নরমালাইজ ও check digit যাচাই।"""
from __future__ import annotations

import re

_PATTERN = re.compile(r"^[A-Z]{3}[UJZ]\d{7}$")


def _letter_values() -> dict[str, int]:
    # A=10, B=12, C=13 ... (11, 22, 33 বাদ যায়)
    values: dict[str, int] = {}
    n = 10
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        if n % 11 == 0:
            n += 1
        values[ch] = n
        n += 1
    return values


_VALUES = _letter_values()


def normalize(raw: str | None) -> str | None:
    """স্পেস/হাইফেন বাদ দিয়ে বড় হাতের অক্ষরে আনে; ISO আকৃতি না হলে None।"""
    if not raw:
        return None
    s = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    if len(s) != 11:
        return None
    # শেষ ৭টি ঘরে শুধু অঙ্ক হবে: সাধারণ OCR ভুল (O->0, I->1) ঠিক করা হয়
    head, tail = s[:4], s[4:].replace("O", "0").replace("I", "1")
    s = head + tail
    return s if _PATTERN.match(s) else None


def check_digit(first10: str) -> int:
    total = 0
    for i, ch in enumerate(first10):
        v = _VALUES[ch] if ch.isalpha() else int(ch)
        total += v * (2**i)
    return total % 11 % 10


def is_valid(number: str | None) -> bool:
    n = normalize(number)
    return n is not None and check_digit(n[:10]) == int(n[10])
