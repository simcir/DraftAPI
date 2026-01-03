from __future__ import annotations

from typing import Optional, Literal
from pydantic import BaseModel, Field


class ChampionRef(BaseModel):
    id: int
    name: str
    slug: str
    img: str = ""


class SideState(BaseModel):
    blue: list[Optional[ChampionRef]]
    red: list[Optional[ChampionRef]]


class DraftState(BaseModel):
    picks: SideState
    bans: SideState


class TargetSlot(BaseModel):
    type: Literal["pick", "ban"]
    side: Literal["blue", "red"]
    idx: int = Field(ge=0)


class DraftRecommendationRequest(BaseModel):
    format: str
    ourSide: Literal["blue", "red"]
    draftState: DraftState
    target: TargetSlot


class RecommendationItem(BaseModel):
    championId: int
    score: float
    reasons: list[str] = []


class DraftRecommendationResponse(BaseModel):
    recommendations: list[RecommendationItem]
