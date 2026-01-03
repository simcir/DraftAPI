from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional

from app.core.config import settings
from app.services.storage.json_repository import JsonRepository
from app.services.storage.data_loader import DataLoader
from app.models.schemas.profile_schemas import (
    RoleProfileOut,
    RoleProfileUpdateIn,
    ProfileChampion,
    ProfileEntryPayload,
)

router = APIRouter()

ROLE_ORDER = ["top", "jungle", "mid", "adc", "support"]

def get_repo():
    return JsonRepository(settings.data_dir)

def get_loader(repo: JsonRepository = Depends(get_repo)):
    return DataLoader(repo)

@router.get("/", response_model=List[str])
def list_profiles(loader: DataLoader = Depends(get_loader)):
    profiles: List[str] = []
    seen = set()
    for role in ROLE_ORDER:
        try:
            profile = loader.role_profile(role)
        except FileNotFoundError:
            continue
        profile_id = profile.get("profile")
        if profile_id and profile_id not in seen:
            profiles.append(profile_id)
            seen.add(profile_id)
    return profiles

@router.get("/entries", response_model=List[ProfileChampion])
def list_entries(profileName: str, role: str, loader: DataLoader = Depends(get_loader)):
    try:
        profile = loader.role_profile(role)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Role profile not found: {role}")
    if profile.get("profile") != profileName:
        return []
    return profile.get("champions", [])

@router.post("/entries", response_model=ProfileChampion)
def create_entry(payload: ProfileEntryPayload, repo: JsonRepository = Depends(get_repo)):
    try:
        profile = repo.read(f"roles/{payload.role}.json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Role profile not found: {payload.role}")
    if profile.get("profile") != payload.profileName:
        raise HTTPException(status_code=400, detail="Profile mismatch between request and role file")

    champions = profile.get("champions", [])
    entry = payload.entry.model_dump()
    entry_id = entry.get("id")
    if any(champ.get("id") == entry_id for champ in champions):
        raise HTTPException(status_code=409, detail="Entry already exists for this champion")

    champions.append(entry)
    profile["champions"] = champions
    repo.write(f"roles/{payload.role}.json", profile)
    return entry

@router.put("/entries/{champion_id}", response_model=ProfileChampion)
def update_entry(champion_id: int, payload: ProfileEntryPayload, repo: JsonRepository = Depends(get_repo)):
    try:
        profile = repo.read(f"roles/{payload.role}.json")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Role profile not found: {payload.role}")
    if profile.get("profile") != payload.profileName:
        raise HTTPException(status_code=400, detail="Profile mismatch between request and role file")

    champions = profile.get("champions", [])
    for idx, champ in enumerate(champions):
        if champ.get("id") == champion_id:
            entry = payload.entry.model_dump()
            entry["id"] = champion_id
            champions[idx] = entry
            profile["champions"] = champions
            repo.write(f"roles/{payload.role}.json", profile)
            return entry

    raise HTTPException(status_code=404, detail="Entry not found")

@router.delete("/entries/{champion_id}")
def delete_entry(
    champion_id: int,
    profileName: Optional[str] = None,
    role: Optional[str] = None,
    repo: JsonRepository = Depends(get_repo),
):
    roles = [role] if role else ROLE_ORDER
    for role_name in roles:
        try:
            profile = repo.read(f"roles/{role_name}.json")
        except FileNotFoundError:
            continue
        if profileName and profile.get("profile") != profileName:
            continue
        champions = profile.get("champions", [])
        new_champions = [champ for champ in champions if champ.get("id") != champion_id]
        if len(new_champions) == len(champions):
            continue
        profile["champions"] = new_champions
        repo.write(f"roles/{role_name}.json", profile)
        return {"deleted": True, "role": role_name, "profileName": profile.get("profile")}

    raise HTTPException(status_code=404, detail="Entry not found")

@router.get("/{role}", response_model=RoleProfileOut)
def get_profile(role: str, loader: DataLoader = Depends(get_loader)):
    try:
        return loader.role_profile(role)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Role profile not found: {role}")

@router.put("/{role}", response_model=RoleProfileOut)
def update_profile(role: str, payload: RoleProfileUpdateIn, repo: JsonRepository = Depends(get_repo)):
    if payload.role != role:
        raise HTTPException(status_code=400, detail="Role mismatch between URL and body")
    repo.write(f"roles/{role}.json", payload.model_dump())
    return payload
