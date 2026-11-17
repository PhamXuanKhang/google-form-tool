"""One-click answer distributions for choice questions.

Every preset returns option percentages that add up to exactly 100, rounded to
two decimals, with any rounding remainder given to the largest option.
Directional presets only make sense when options are ordered (a scale), so
they are offered for ordered questions only.
"""
from __future__ import annotations

import math
from typing import Dict, List

UNIFORM = "uniform"
POSITIVE_SKEW = "positive_skew"
NEGATIVE_SKEW = "negative_skew"
BELL = "bell"
FIRST_HEAVY = "first_heavy"

ORDERED_PRESETS = (UNIFORM, POSITIVE_SKEW, NEGATIVE_SKEW, BELL, FIRST_HEAVY)
UNORDERED_PRESETS = (UNIFORM, FIRST_HEAVY)
PRESETS = ORDERED_PRESETS

# Question types whose options form a scale.
ORDERED_TYPES = {"linear_scale", "rating"}
# Question types where one option is picked and percentages share 100.
PRESET_TYPES = {"multiple_choice", "dropdown", "linear_scale", "rating"}

FIRST_HEAVY_SHARE = 0.6


def presets_for(question_type: str) -> tuple:
    if question_type not in PRESET_TYPES:
        return ()
    return ORDERED_PRESETS if question_type in ORDERED_TYPES else UNORDERED_PRESETS


def _weights(option_count: int, preset: str) -> List[float]:
    n = option_count
    if preset == UNIFORM:
        return [1.0] * n
    if preset == POSITIVE_SKEW:
        return [float(i + 1) for i in range(n)]
    if preset == NEGATIVE_SKEW:
        return [float(n - i) for i in range(n)]
    if preset == BELL:
        center = (n - 1) / 2
        spread = max(n / 4, 0.75)
        return [math.exp(-((i - center) ** 2) / (2 * spread ** 2)) for i in range(n)]
    if preset == FIRST_HEAVY:
        if n == 1:
            return [1.0]
        rest = (1 - FIRST_HEAVY_SHARE) / (n - 1)
        return [FIRST_HEAVY_SHARE] + [rest] * (n - 1)
    raise ValueError(f"Unknown preset '{preset}'. Expected one of: {', '.join(PRESETS)}")


def apply_preset(option_count: int, preset: str, ordered: bool) -> List[float]:
    """Percentages for ``option_count`` options under ``preset``; they sum to 100."""
    if not isinstance(option_count, int) or option_count < 1:
        raise ValueError("A preset needs at least one option.")
    if preset not in PRESETS:
        raise ValueError(f"Unknown preset '{preset}'. Expected one of: {', '.join(PRESETS)}")
    if not ordered and preset not in UNORDERED_PRESETS:
        raise ValueError(f"Preset '{preset}' only applies to scale questions.")

    weights = _weights(option_count, preset)
    total = sum(weights)
    hundredths = [round(weight / total * 10000) for weight in weights]
    # Settle the rounding remainder one hundredth at a time, largest options first.
    largest_first = sorted(range(option_count), key=lambda index: -weights[index])
    remainder = 10000 - sum(hundredths)
    step = 1 if remainder > 0 else -1
    for k in range(abs(remainder)):
        hundredths[largest_first[k % option_count]] += step
    return [value / 100 for value in hundredths]


def preset_table(option_count: int, question_type: str) -> Dict[str, List[float]]:
    """Every preset available for a question, with its percentages."""
    ordered = question_type in ORDERED_TYPES
    return {name: apply_preset(option_count, name, ordered) for name in presets_for(question_type)}
