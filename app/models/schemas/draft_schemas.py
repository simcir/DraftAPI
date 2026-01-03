from pydantic import BaseModel, Field
from typing import List, Literal

Side = Literal["blue", "red"]
ActionType = Literal["pick", "ban"]
DraftMode = Literal["flex", "tournament"]
DraftStatus = Literal["building", "full"]

class DraftCreateIn(BaseModel):
    mode: DraftMode = "flex"

class DraftSideState(BaseModel):
    picks: List[int] = Field(default_factory=list)
    bans: List[int] = Field(default_factory=list)

class DraftTurn(BaseModel):
    phaseIndex: int
    sideToAct: Side
    type: ActionType
    remainingInPhase: int

class DraftStateOut(BaseModel):
    draftId: str
    mode: DraftMode
    status: DraftStatus
    blue: DraftSideState
    red: DraftSideState
    turn: DraftTurn

class DraftActionIn(BaseModel):
    type: ActionType
    side: Side
    championId: int
