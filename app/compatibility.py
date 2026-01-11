from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Tuple


ARCHETYPES = ["kasif", "savasci", "stratejist", "sifaci"]


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def sigmoid(x: float) -> float:
    # numerically stable sigmoid
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def to_unit_vector(archetype_scores: Dict[str, float]) -> List[float]:
    v = [float(archetype_scores.get(k, 0.0)) for k in ARCHETYPES]
    norm = math.sqrt(sum(x * x for x in v))
    if norm <= 1e-9:
        # degenerate case: return a neutral unit vector
        return [0.5, 0.5, 0.5, 0.5]
    return [x / norm for x in v]


def cosine_similarity(a: List[float], b: List[float]) -> float:
    # both should be unit vectors; still clamp for safety
    dot = sum(x * y for x, y in zip(a, b))
    return clamp((dot + 1.0) / 2.0, 0.0, 1.0)  # map [-1,1] to [0,1]


def profile_diversity(archetype_scores: Dict[str, float]) -> float:
    """
    Measures how 'non-flat' a profile is.
    - If all archetypes are similar => diversity low (penalize)
    - If there is a clearer differentiation => diversity higher (bonus)
    Output: 0..1
    """
    vals = [float(archetype_scores.get(k, 0.0)) for k in ARCHETYPES]
    if not vals:
        return 0.5
    mean = sum(vals) / len(vals)
    var = sum((x - mean) ** 2 for x in vals) / len(vals)
    # map variance to 0..1 with a soft saturation
    # tweak 0.18 based on your score scale; works well if scores ~0..10
    return clamp(var / (var + 0.18), 0.0, 1.0)


def tag_similarity(tags_a: Dict[str, float] | None, tags_b: Dict[str, float] | None) -> float:
    """
    tags_*: e.g. {"iletisim": 0.8, "risk": 0.2, ...} in 0..1
    If tags are missing, return neutral 0.5 (doesn't distort).
    """
    if not tags_a or not tags_b:
        return 0.5

    keys = sorted(set(tags_a.keys()) | set(tags_b.keys()))
    if not keys:
        return 0.5

    # similarity = 1 - normalized L1 distance
    dist = 0.0
    for k in keys:
        dist += abs(float(tags_a.get(k, 0.5)) - float(tags_b.get(k, 0.5)))

    # max dist per key is 1.0, so normalize by len(keys)
    dist /= len(keys)
    return clamp(1.0 - dist, 0.0, 1.0)


@dataclass(frozen=True)
class CompatibilityBreakdown:
    sim: float
    div: float
    tag_sim: float
    raw: float
    shaped: float
    noise: float
    final01: float
    score: int


def compute_compatibility_score(
    profile_a: Dict[str, float],
    profile_b: Dict[str, float],
    tags_a: Dict[str, float] | None = None,
    tags_b: Dict[str, float] | None = None,
    seed: str | None = None,
) -> CompatibilityBreakdown:
    """
    Returns score 0..100 and a breakdown for 'why compatible?' UI.
    seed: pass a stable seed (e.g. f"{userA_id}:{userB_id}") to keep scores consistent between sessions.
    """
    # stable randomness for a pair (optional)
    rng = random.Random(seed) if seed else random.Random()

    va = to_unit_vector(profile_a)
    vb = to_unit_vector(profile_b)

    sim = cosine_similarity(va, vb)                    # 0..1
    div = (profile_diversity(profile_a) + profile_diversity(profile_b)) / 2.0  # 0..1
    tag_sim = tag_similarity(tags_a, tags_b)           # 0..1

    # composite raw score
    raw = 0.62 * sim + 0.23 * tag_sim + 0.15 * div     # 0..1-ish
    raw = clamp(raw, 0.0, 1.0)

    # shape distribution (sigmoid)
    shaped = sigmoid((raw - 0.5) * 5.4)                # 0..1, more spread

    # controlled noise (less noise for higher compatibility)
    epsilon = 0.02 + 0.05 * (1.0 - shaped)             # 0.02..0.06
    noise = rng.uniform(-epsilon, +epsilon)

    final01 = clamp(shaped + noise, 0.0, 1.0)

    # map to 0..100 with a floor
    score = int(round(6 + 90 * final01))

    return CompatibilityBreakdown(
        sim=sim,
        div=div,
        tag_sim=tag_sim,
        raw=raw,
        shaped=shaped,
        noise=noise,
        final01=final01,
        score=score,
    )
