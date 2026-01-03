from __future__ import annotations

from typing import Iterable, List, Set, Tuple

from app.models.schemas.recommendation_schemas import DraftRecommendationRequest, RecommendationItem
from app.services.scoring.color_rules import color_bonus
from app.services.storage.data_loader import DataLoader

# TODO for the moment >= after we will swap depending on which champion in enemy team are picked >= we need to modify champion.json to put the role so we know what role in enemy are picked !
ROLE_ORDER = ["top", "jungle", "mid", "adc", "support"]

def build_recommendations(payload: DraftRecommendationRequest, loader: DataLoader) -> List[RecommendationItem]:
    our_picks = _champion_ids(getattr(payload.draftState.picks, payload.ourSide))
    enemy_side = "red" if payload.ourSide == "blue" else "blue"
    enemy_picks = _champion_ids(getattr(payload.draftState.picks, enemy_side))

    champions = None
    try:
        champions = loader.champions()
    except FileNotFoundError:
        pass

    remaining_roles = _remaining_roles(our_picks, champions)
    enemy_roles = _picked_roles(enemy_picks, champions)
    if enemy_roles:
        role_order = [role for role in enemy_roles if role in remaining_roles]
        if not role_order:
            role_order = remaining_roles
    else:
        role_order = remaining_roles

    roles_profiles = _pick_roles(loader, role_order)


    if not roles_profiles:
        return []

    blocked_ids = _blocked_champions(payload)

    recommendations: List[RecommendationItem] = []
    for role, profile in roles_profiles:
        for champ in profile.get("champions", []):
            champ_id = champ.get("id")
            if champ_id in blocked_ids:
                continue
            score, reasons = _score_champion(champ, payload.ourSide, our_picks, enemy_picks)
            if role:
                reasons.append(f"role focus: {role}")
            recommendations.append(
                RecommendationItem(
                    championId=champ_id,
                    score=score,
                    reasons=reasons,
                )
            )

    recommendations.sort(key=lambda item: item.score, reverse=True)
    return recommendations

def _remaining_roles(our_picks: Set[int], champions: List[dict] | None) -> List[str]:
    if not our_picks or not champions:
        return ROLE_ORDER
    picked_roles: Set[str] = set()
    for champ in champions:
        champ_id = champ.get("id")
        if champ_id in our_picks:
            picked_roles.update(champ.get("roles", []))
            if len(picked_roles) == len(ROLE_ORDER):
                return ROLE_ORDER
    remaining = [role for role in ROLE_ORDER if role not in picked_roles]
    return remaining or ROLE_ORDER

def _picked_roles(pick_ids: Set[int], champions: List[dict] | None) -> List[str]:
    if not pick_ids or not champions:
        return []
    picked_roles: Set[str] = set()
    for champ in champions:
        champ_id = champ.get("id")
        if champ_id in pick_ids:
            picked_roles.update(champ.get("roles", []))
            if len(picked_roles) == len(ROLE_ORDER):
                break
    return [role for role in ROLE_ORDER if role in picked_roles]

def _pick_roles(loader: DataLoader, role_order: List[str]) -> List[Tuple[str, dict]]:
    roles_profiles: List[Tuple[str, dict]] = []
    for role in role_order:
        try:
            profile = loader.role_profile(role)
        except FileNotFoundError:
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

def _score_champion(profile_champ: dict, our_side: str, our_picks: Set[int], enemy_picks: Set[int]) -> Tuple[float, List[str]]:
    reasons: List[str] = []

    how_good = profile_champ.get("howGoodIAm", 0)
    meta = profile_champ.get("meta", 0)
    score = how_good * 1.5 + meta * 1.0
    if how_good:
        reasons.append(f"comfort {how_good}/10")
    if meta:
        reasons.append(f"meta {meta}/10")

    colors = profile_champ.get("colors", [])
    color_score, color_reasons = color_bonus(our_side, colors)
    score += color_score
    reasons.extend(color_reasons)

    synergy = _matching_count(profile_champ.get("synergy", []), our_picks)
    if synergy:
        score += 0.75 * synergy
        reasons.append(f"synergy with {synergy} pick(s)")

    counters = _matching_count(profile_champ.get("counters", []), enemy_picks)
    if counters:
        score += 0.6 * counters
        reasons.append(f"counters {counters} enemy pick(s)")

    strong_into = _matching_count(profile_champ.get("strongInto", []), enemy_picks)
    if strong_into:
        score += 1.0 * strong_into
        reasons.append(f"strong into {strong_into} enemy pick(s)")

    return score, reasons

def _matching_count(reference_ids: Iterable[int], target_ids: Set[int]) -> int:
    count = 0
    for champ_id in reference_ids:
        if champ_id in target_ids:
            count += 1
    return count
