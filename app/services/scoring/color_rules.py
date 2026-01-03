from __future__ import annotations

from typing import Tuple, List

def color_bonus(our_side: str, colors: List[str]) -> Tuple[float, List[str]]:
    if not colors:
        return 0.0, []

    bonus = 0.0
    reasons: List[str] = []
    if our_side in colors:
        bonus += 1.5
        reasons.append(f"color match ({our_side})")

    return bonus, reasons
