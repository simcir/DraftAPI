from __future__ import annotations

from typing import Dict, Iterable, List, Tuple

MULTIPLIER_KEYS = (
    "base",
    "synergyMultiplier",
    "counterMultiplier",
    "strongIntoMultiplier",
    "teamColorBonus",
)

def _default_multipliers(color_rules: Dict) -> Dict[str, float]:
    defaults = color_rules.get("defaults", {}) if color_rules else {}
    multipliers = {}
    for key in MULTIPLIER_KEYS:
        multipliers[key] = float(defaults.get(key, 1.0 if key != "teamColorBonus" else 0.0))
    return multipliers

def color_multipliers(champion_colors: Iterable[str], color_rules: Dict) -> Dict[str, float]:
    multipliers = _default_multipliers(color_rules)
    for color in champion_colors or []:
        modifiers = (color_rules.get(color, {}) or {}).get("modifiers", {})
        for key in multipliers:
            multipliers[key] = max(multipliers[key], float(modifiers.get(key, multipliers[key])))
    return multipliers

def team_color_bonus(
    champion_colors: Iterable[str],
    team_color_counts: Dict[str, int],
    color_rules: Dict,
) -> Tuple[float, List[str]]:
    bonus = 0.0
    reasons: List[str] = []
    for color in champion_colors or []:
        modifiers = (color_rules.get(color, {}) or {}).get("modifiers", {})
        base_bonus = float(modifiers.get("teamColorBonus", 0.0))
        if base_bonus:
            bonus += base_bonus
            reasons.append(f"team color bonus ({color})")

        for condition in modifiers.get("conditions", []) or []:
            if condition.get("if") != "team_has_same_color":
                continue
            target_color = condition.get("color", color)
            minimum = int(condition.get("min", 1))
            if team_color_counts.get(target_color, 0) >= minimum:
                condition_bonus = float(condition.get("bonus", 0.0))
                if condition_bonus:
                    bonus += condition_bonus
                    reasons.append(f"stacked {target_color} bonus")

    return bonus, reasons
