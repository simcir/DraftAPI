from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional

from app.core.config import settings
from app.services.storage.json_repository import JsonRepository
from app.services.storage.data_loader import DataLoader
from app.models.schemas.profile_schemas import (
    RoleProfileOut,
    RoleProfileSummary,
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

def _read_role_store(repo: JsonRepository, role: str):
    return DataLoader(repo).role_store(role)

def _write_role_store(repo: JsonRepository, role: str, store: dict):
    repo.write(f"roles/{role}.json", store)

def _find_profile(store: dict, profile_name: str):
    for profile in store["profiles"]:
        if profile.get("profile") == profile_name:
            return profile
    return None

@router.get("/", response_model=List[str])
def list_profiles(loader: DataLoader = Depends(get_loader)):
    try:
        profiles = loader.role_profiles()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Role profile not found: {exc.filename}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return [profile["profile"] for profile in profiles]

@router.get("/assignments", response_model=List[RoleProfileSummary])
def list_profile_assignments(loader: DataLoader = Depends(get_loader)):
    try:
        profiles = loader.role_profiles()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Role profile not found: {exc.filename}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return [
        RoleProfileSummary(profile=profile["profile"], role=profile["role"])
        for profile in profiles
    ]

@router.get("/catalog", response_model=List[RoleProfileSummary])
def list_profile_catalog(loader: DataLoader = Depends(get_loader)):
    catalog: List[RoleProfileSummary] = []
    try:
        for role in ROLE_ORDER:
            store = loader.role_store(role)
            for profile in store["profiles"]:
                catalog.append(RoleProfileSummary(profile=profile["profile"], role=role))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Role profile not found: {exc.filename}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return catalog

@router.get("/entries", response_model=List[ProfileChampion])
def list_entries(profileName: str, role: str, loader: DataLoader = Depends(get_loader)):
    try:
        profile = loader.role_profile(role, profileName)
    except FileNotFoundError:
        return []
    if profile.get("profile") != profileName:
        return []
    return profile.get("champions", [])

@router.post("/entries", response_model=ProfileChampion)
def create_entry(payload: ProfileEntryPayload, repo: JsonRepository = Depends(get_repo)):
    try:
        store = _read_role_store(repo, payload.role)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Role profile not found: {payload.role}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    profile = _find_profile(store, payload.profileName)
    if profile is None:
        profile = {
            "profile": payload.profileName,
            "role": payload.role,
            "champions": [],
        }
        store["profiles"].append(profile)

    champions = profile.get("champions", [])
    entry = payload.entry.model_dump()
    entry_id = entry.get("id")
    if any(champ.get("id") == entry_id for champ in champions):
        raise HTTPException(status_code=409, detail="Entry already exists for this champion")

    champions.append(entry)
    profile["champions"] = champions
    _write_role_store(repo, payload.role, store)
    return entry

@router.put("/entries/{champion_id}", response_model=ProfileChampion)
def update_entry(champion_id: int, payload: ProfileEntryPayload, repo: JsonRepository = Depends(get_repo)):
    try:
        store = _read_role_store(repo, payload.role)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Role profile not found: {payload.role}")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    profile = _find_profile(store, payload.profileName)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    champions = profile.get("champions", [])
    for idx, champ in enumerate(champions):
        if champ.get("id") == champion_id:
            entry = payload.entry.model_dump()
            entry["id"] = champion_id
            champions[idx] = entry
            profile["champions"] = champions
            _write_role_store(repo, payload.role, store)
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
            store = _read_role_store(repo, role_name)
        except FileNotFoundError:
            continue
        except ValueError:
            continue
        candidate_profiles = store["profiles"]
        if profileName:
            candidate_profiles = [profile for profile in candidate_profiles if profile.get("profile") == profileName]
        for profile in candidate_profiles:
            champions = profile.get("champions", [])
            new_champions = [champ for champ in champions if champ.get("id") != champion_id]
            if len(new_champions) == len(champions):
                continue
            profile["champions"] = new_champions
            _write_role_store(repo, role_name, store)
            return {"deleted": True, "role": role_name, "profileName": profile.get("profile")}

    raise HTTPException(status_code=404, detail="Entry not found")

@router.get("/{role}", response_model=RoleProfileOut)
def get_profile(role: str, loader: DataLoader = Depends(get_loader)):
    try:
        profile = loader.role_profile(role)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Role profile not found: {role}")
    if profile.get("role") != role:
        raise HTTPException(status_code=400, detail=f"Role profile mismatch for {role}")
    return profile

@router.put("/{role}", response_model=RoleProfileOut)
def update_profile(role: str, payload: RoleProfileUpdateIn, repo: JsonRepository = Depends(get_repo)):
    if payload.role != role:
        raise HTTPException(status_code=400, detail="Role mismatch between URL and body")
    try:
        store = _read_role_store(repo, role)
    except FileNotFoundError:
        store = {"role": role, "activeProfile": payload.profile, "profiles": []}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    profile = _find_profile(store, payload.profile)
    if profile is None:
        store["profiles"].append(payload.model_dump())
    else:
        profile.update(payload.model_dump())
    store["activeProfile"] = payload.profile
    _write_role_store(repo, role, store)
    return payload
