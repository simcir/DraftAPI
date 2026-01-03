from fastapi import APIRouter, Depends, HTTPException
from app.core.config import settings
from app.services.storage.json_repository import JsonRepository
from app.services.storage.data_loader import DataLoader
from app.models.schemas.profile_schemas import RoleProfileOut, RoleProfileUpdateIn

router = APIRouter()

def get_repo():
    return JsonRepository(settings.data_dir)

def get_loader(repo: JsonRepository = Depends(get_repo)):
    return DataLoader(repo)

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
