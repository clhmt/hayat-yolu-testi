from __future__ import annotations

import math
from typing import Dict, Tuple


ZODIAC_ELEMENT = {
    "Koç": "Fire",
    "Aslan": "Fire",
    "Yay": "Fire",
    "Boğa": "Earth",
    "Başak": "Earth",
    "Oğlak": "Earth",
    "İkizler": "Air",
    "Terazi": "Air",
    "Kova": "Air",
    "Yengeç": "Water",
    "Akrep": "Water",
    "Balık": "Water",
}

ELEMENT_BONUS = {
    ("Fire", "Fire"): 15,
    ("Earth", "Earth"): 15,
    ("Air", "Air"): 15,
    ("Water", "Water"): 15,
    ("Fire", "Air"): 12,
    ("Air", "Fire"): 12,
    ("Earth", "Water"): 12,
    ("Water", "Earth"): 12,
}


def _cosine_similarity(a: Dict[str, int], b: Dict[str, int]) -> float:
    keys = set(a.keys()) | set(b.keys())
    if not keys:
        return 0.0
    dot = 0.0
    na = 0.0
    nb = 0.0
    for k in keys:
        va = float(a.get(k, 0))
        vb = float(b.get(k, 0))
        dot += va * vb
        na += va * va
        nb += vb * vb
    if na <= 0 or nb <= 0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def _label(score: int) -> str:
    if score >= 85:
        return "Çok Uyumlu"
    if score >= 70:
        return "Uyumlu"
    if score >= 55:
        return "Orta"
    if score >= 40:
        return "Zorlayıcı"
    return "Çatışmalı"


def compute_compatibility(
    totals_a: Dict[str, int],
    totals_b: Dict[str, int],
    zodiac_a: str,
    zodiac_b: str,
) -> Tuple[int, str, Dict[str, int]]:
    """
    0-100 skor + etiket + breakdown döndürür.
    breakdown:
      - sim_pct: 0..100
      - element_bonus: 0..15
      - variety_bonus: 0..12
    """
    sim = _cosine_similarity(totals_a or {}, totals_b or {})
    base = int(round(sim * 70))

    ea = ZODIAC_ELEMENT.get(zodiac_a, "")
    eb = ZODIAC_ELEMENT.get(zodiac_b, "")
    element_bonus = ELEMENT_BONUS.get((ea, eb), 6 if ea and eb else 0)

    dom_a = max(totals_a, key=totals_a.get) if totals_a else ""
    dom_b = max(totals_b, key=totals_b.get) if totals_b else ""
    variety_bonus = 12 if (dom_a and dom_b and dom_a != dom_b) else 6

    score = max(0, min(100, base + element_bonus + variety_bonus))
    label = _label(score)

    breakdown = {
        "sim_pct": int(round(sim * 100)),
        "element_bonus": int(element_bonus),
        "variety_bonus": int(variety_bonus),
    }
    return score, label, breakdown
