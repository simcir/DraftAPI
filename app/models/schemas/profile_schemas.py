from pydantic import BaseModel, Field
from typing import List

class ProfileChampion(BaseModel):
    id: int
    howGoodIAm: int = Field(ge=0, le=10)
    colors: List[str] = Field(default_factory=list)
    synergy: List[int] = Field(default_factory=list)
    counters: List[int] = Field(default_factory=list)
    strongInto: List[int] = Field(default_factory=list)
    meta: int = Field(default=0, ge=0, le=10)

class RoleProfileOut(BaseModel):
    profile: str
    role: str
    champions: List[ProfileChampion]

class RoleProfileUpdateIn(RoleProfileOut):
    pass


class ProfileEntryPayload(BaseModel):
    profileName: str
    role: str
    entry: ProfileChampion

