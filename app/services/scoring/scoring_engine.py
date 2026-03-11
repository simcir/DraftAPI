from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple

from app.models.schemas.recommendation_schemas import DraftRecommendationRequest, RecommendationItem
from app.services.scoring.color_rules import color_multipliers, team_color_bonus
from app.services.storage.data_loader import DataLoader, ROLE_ORDER


def build_recommendations(payload: DraftRecommendationRequest, loader: DataLoader) -> List[RecommendationItem]:
    profiles_by_role = _load_profiles_by_role(loader)
    our_pick_slots = getattr(payload.draftState.picks, payload.ourSide)
    _validate_pick_slots(our_pick_slots, payload.ourSide)
    our_picks = _champion_ids(our_pick_slots)
    enemy_side = "red" if payload.ourSide == "blue" else "blue"
    enemy_pick_slots = getattr(payload.draftState.picks, enemy_side)
    _validate_pick_slots(enemy_pick_slots, enemy_side)
    enemy_picks = _champion_ids(enemy_pick_slots)
    champion_role_index = _load_champion_role_index(loader)

    locked_our_roles = _infer_locked_roles(our_pick_slots, champion_role_index)
    locked_enemy_roles = _infer_locked_roles(enemy_pick_slots, champion_role_index)
    scoring_weights = _load_scoring_weights(loader)
    enemy_role_weights = _enemy_role_weights(
        locked_enemy_roles,
        locked_our_roles,
        scoring_weights,
    )
    remaining_roles = _remaining_roles(locked_our_roles)
    role_order = _prioritized_roles(remaining_roles, enemy_role_weights)

    roles_profiles = _pick_roles(profiles_by_role, role_order)
    color_rules = _load_color_rules(loader)
    color_index = _build_color_index(profiles_by_role)
    team_color_counts = _team_color_counts(our_picks, color_index)
    target_colors = _target_team_colors(team_color_counts)


    if not roles_profiles:
        return []

    blocked_ids = _blocked_champions(payload)

    recommendations_by_id: Dict[int, RecommendationItem] = {}
    for role, profile in roles_profiles:
        for champ in profile.get("champions", []):
            champ_id = champ.get("id")
            if champ_id in blocked_ids:
                continue
            score, reasons = _score_champion(
                champ,
                scoring_weights,
                color_rules,
                team_color_counts,
                target_colors,
                role,
                enemy_role_weights,
                our_picks,
                enemy_picks,
            )
            if role:
                reasons.append(f"role focus: {role}")
            item = RecommendationItem(
                championId=champ_id,
                score=score,
                roles=[role] if role else [],
                reasons=reasons,
            )
            existing = recommendations_by_id.get(champ_id)
            if existing is None:
                recommendations_by_id[champ_id] = item
                continue
            existing.score = max(existing.score, item.score)
            existing.roles = _merge_roles(existing.roles, item.roles)
            existing.reasons = _merge_reasons(existing.reasons, item.reasons)

    recommendations = list(recommendations_by_id.values())
    recommendations.sort(key=lambda item: item.score, reverse=True)
    _log_recommendations(
        recommendations,
        enemy_role_weights,
        locked_our_roles,
        locked_enemy_roles,
        remaining_roles,
        role_order,
    )
    return recommendations

def _remaining_roles(locked_roles: Set[str]) -> List[str]:
    if not locked_roles:
        return ROLE_ORDER
    remaining = [role for role in ROLE_ORDER if role not in locked_roles]
    return remaining or ROLE_ORDER

def _validate_pick_slots(champions: List, side: str) -> None:
    if len(champions) != len(ROLE_ORDER):
        raise ValueError(
            f"{side} picks must contain exactly {len(ROLE_ORDER)} role slots ordered as "
            f"{', '.join(ROLE_ORDER)}"
        )

def _load_profiles_by_role(loader: DataLoader) -> Dict[str, dict]:
    return {profile["role"]: profile for profile in loader.role_profiles()}

def _load_champion_role_index(loader: DataLoader) -> Dict[int, Set[str]]:
    try:
        champions = loader.champions()
    except FileNotFoundError:
        return {}
    role_index: Dict[int, Set[str]] = {}
    for champion in champions:
        champ_id = champion.get("id")
        if champ_id is None:
            continue
        roles = champion.get("roles", [])
        if not roles:
            continue
        role_index[champ_id] = set(roles)
    return role_index

def _prioritized_roles(remaining_roles: List[str], enemy_role_weights: Dict[str, float]) -> List[str]:
    if not remaining_roles:
        return ROLE_ORDER
    return sorted(
        remaining_roles,
        key=lambda role: (-enemy_role_weights.get(role, 1.0), ROLE_ORDER.index(role)),
    )

def _pick_roles(profiles_by_role: Dict[str, dict], role_order: List[str]) -> List[Tuple[str, dict]]:
    roles_profiles: List[Tuple[str, dict]] = []
    for role in role_order:
        profile = profiles_by_role.get(role)
        if profile is None:
            continue
        if profile.get("champions"):
            roles_profiles.append((role, profile))
    return roles_profiles

def _blocked_champions(payload: DraftRecommendationRequest) -> Set[int]:
    picks = payload.draftState.picks
    bans = payload.draftState.bans
    ids = set()
    ids.update(_champion_ids(picks.blue))
    ids.update(_champion_ids(picks.red))
    ids.update(_champion_ids(bans.blue))
    ids.update(_champion_ids(bans.red))
    return ids

def _champion_ids(champions: Iterable) -> Set[int]:
    ids: Set[int] = set()
    for champ in champions:
        if champ is None:
            continue
        champ_id = getattr(champ, "id", None)
        if champ_id is None:
            champ_id = champ.get("id") if isinstance(champ, dict) else None
        if champ_id is not None:
            ids.add(champ_id)
    return ids

def _score_champion(
    profile_champ: dict,
    scoring_weights: Dict[str, float],
    color_rules: Dict,
    team_color_counts: Dict[str, int],
    target_colors: List[str],
    role: str,
    enemy_role_weights: Dict[str, float],
    our_picks: Set[int],
    enemy_picks: Set[int],
) -> Tuple[float, List[str]]:
    reasons: List[str] = []
    colors = profile_champ.get("colors", [])
    multipliers = color_multipliers(colors, color_rules)

    # Step 1: Base comfort + meta contribution.
    how_good = profile_champ.get("howGoodIAm", 0)
    meta = profile_champ.get("meta", 0)
    score = (
        how_good * _weight(scoring_weights, "howGoodIAm", 0.0)
        + meta * _weight(scoring_weights, "meta", 0.0)
    ) * multipliers["base"]
    if how_good:
        reasons.append(f"comfort {how_good}/10")
    if meta:
        reasons.append(f"meta {meta}/10")

    # Step 2: Align with the two-color plan (if the team already shows a direction).
    if target_colors:
        matched_colors = [color for color in colors if color in target_colors]
        if matched_colors:
            score += _weight(scoring_weights, "colorFit", 0.0) * len(matched_colors)
            reasons.append(f"team colors: {', '.join(matched_colors)}")

    # Step 3: Role nuance: counter-pick role gets a big multiplier, ADC gets a small flex multiplier.
    role_multiplier = 1.0
    if role:
        role_multiplier = enemy_role_weights.get(role, 1.0)
        if role_multiplier > 1.0:
            reasons.append(f"role counter focus: {role}")
        elif role == "adc":
            role_multiplier = _weight(scoring_weights, "adcFlexMultiplier", 1.0)
            if role_multiplier > 1.0:
                reasons.append("adc flex priority")
    if role_multiplier != 1.0:
        score *= role_multiplier

    # Step 4: Synergy with our picks (color multipliers can boost this).
    synergy = _matching_count(profile_champ.get("synergy", []), our_picks)
    if synergy:
        score += _weight(scoring_weights, "synergy", 0.0) * multipliers["synergyMultiplier"] * synergy
        reasons.append(f"synergy with {synergy} pick(s)")

    # Step 5: Counter + strong-into vs enemy picks (green/red multipliers matter here).
    counters = _matching_count(profile_champ.get("counters", []), enemy_picks)
    if counters:
        counter_multiplier = multipliers["counterMultiplier"]
        penalty_multiplier = _weight(scoring_weights, "counterPenaltyMultiplier", 0.7)
        score -= _weight(scoring_weights, "counters", 0.0) * counter_multiplier * penalty_multiplier * counters
        reasons.append(f"countered by {counters} enemy pick(s)")

    strong_into = _matching_count(profile_champ.get("strongInto", []), enemy_picks)
    if strong_into:
        score += _weight(scoring_weights, "strongInto", 0.0) * multipliers["strongIntoMultiplier"] * strong_into
        reasons.append(f"strong into {strong_into} enemy pick(s)")

    # Step 6: Bonus for stacking specific colors (ex: white scaling bonuses).
    color_bonus, color_reasons = team_color_bonus(colors, team_color_counts, color_rules)
    if color_bonus:
        score += color_bonus
        reasons.extend(color_reasons)

    return score, reasons

def _matching_count(reference_ids: Iterable[int], target_ids: Set[int]) -> int:
    count = 0
    for champ_id in reference_ids:
        if champ_id in target_ids:
            count += 1
    return count

def _merge_reasons(left: List[str], right: List[str]) -> List[str]:
    merged: List[str] = []
    seen: Set[str] = set()
    for reason in [*left, *right]:
        if reason in seen:
            continue
        seen.add(reason)
        merged.append(reason)
    return merged

def _merge_roles(left: List[str], right: List[str]) -> List[str]:
    merged: List[str] = []
    seen: Set[str] = set()
    for role in [*left, *right]:
        if role in seen:
            continue
        seen.add(role)
        merged.append(role)
    return sorted(merged, key=ROLE_ORDER.index)

def _infer_locked_roles(champions: Iterable, role_index: Dict[int, Set[str]]) -> Set[str]:
    candidate_roles: List[List[str]] = []
    for champ in champions:
        if champ is None:
            continue
        champ_id = getattr(champ, "id", None)
        if champ_id is None and isinstance(champ, dict):
            champ_id = champ.get("id")
        if champ_id is None:
            continue
        roles = sorted(role_index.get(champ_id, []), key=ROLE_ORDER.index)
        if roles:
            candidate_roles.append(roles)
    return _best_role_assignment(candidate_roles)

def _best_role_assignment(candidate_roles: List[List[str]]) -> Set[str]:
    if not candidate_roles:
        return set()

    ordered_candidates = sorted(candidate_roles, key=len)
    best_assignment: Set[str] = set()

    def backtrack(idx: int, used_roles: Set[str]) -> None:
        nonlocal best_assignment
        if len(used_roles) > len(best_assignment):
            best_assignment = set(used_roles)
        if idx >= len(ordered_candidates):
            return
        remaining = len(ordered_candidates) - idx
        if len(used_roles) + remaining <= len(best_assignment):
            return

        roles = ordered_candidates[idx]
        for role in roles:
            if role in used_roles:
                continue
            used_roles.add(role)
            backtrack(idx + 1, used_roles)
            used_roles.remove(role)

        backtrack(idx + 1, used_roles)

    backtrack(0, set())
    return best_assignment

def _load_scoring_weights(loader: DataLoader) -> Dict[str, float]:
    try:
        data = loader.scoring_weights()
    except FileNotFoundError:
        return {}
    return data.get("weights", {}) or {}

def _weight(scoring_weights: Dict[str, float], key: str, default: float) -> float:
    value = scoring_weights.get(key)
    if value is None:
        return default
    return float(value)

def _load_color_rules(loader: DataLoader) -> Dict:
    try:
        return loader.color_rules()
    except FileNotFoundError:
        return {}

def _build_color_index(profiles_by_role: Dict[str, dict]) -> Dict[int, Set[str]]:
    index: Dict[int, Set[str]] = {}
    for role in ROLE_ORDER:
        profile = profiles_by_role.get(role)
        if profile is None:
            continue
        for champ in profile.get("champions", []):
            champ_id = champ.get("id")
            if champ_id is None:
                continue
            if champ_id not in index:
                index[champ_id] = set()
            index[champ_id].update(champ.get("colors", []))
    return index

def _enemy_role_weights(
    locked_enemy_roles: Set[str],
    locked_our_roles: Set[str],
    scoring_weights: Dict[str, float],
) -> Dict[str, float]:
    weights: Dict[str, float] = {}
    for role in locked_enemy_roles:
        if role in locked_our_roles:
            continue
        weights[role] = max(weights.get(role, 1.0), _weight(scoring_weights, "roleCounterMultiplier", 1.0))
    return weights

def _team_color_counts(our_picks: Set[int], color_index: Dict[int, Set[str]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for champ_id in our_picks:
        for color in color_index.get(champ_id, []):
            counts[color] = counts.get(color, 0) + 1
    return counts

def _target_team_colors(team_color_counts: Dict[str, int]) -> List[str]:
    if not team_color_counts:
        return []
    ordered = sorted(team_color_counts.items(), key=lambda item: (-item[1], item[0]))
    return [color for color, _count in ordered[:2]]

def _log_recommendations(
    recommendations: List[RecommendationItem],
    enemy_role_weights: Dict[str, float],
    locked_our_roles: Set[str],
    locked_enemy_roles: Set[str],
    remaining_roles: List[str],
    prioritized_roles: List[str],
) -> None:
    top = recommendations[:5]
    print("=== Draft Advisor: Top 5 Recommendations ===")
    if enemy_role_weights:
        ordered_roles = sorted(enemy_role_weights.items(), key=lambda item: (-item[1], item[0]))
        role_text = ", ".join(f"{role} x{weight:.2f}" for role, weight in ordered_roles)
    else:
        role_text = "none"
    print(f"Enemy role priority: {role_text}")
    print(f"Our locked roles: {', '.join(sorted(locked_our_roles)) or 'none'}")
    print(f"Enemy locked roles: {', '.join(sorted(locked_enemy_roles)) or 'none'}")
    print(f"Remaining roles: {', '.join(remaining_roles)}")
    print(f"Prioritized roles: {', '.join(prioritized_roles)}")
    if not top:
        print("No recommendations available.")
        return
    for idx, item in enumerate(top, start=1):
        print(f"{idx}. champId={item.championId} score={item.score:.2f} reasons={'; '.join(item.reasons)}")
