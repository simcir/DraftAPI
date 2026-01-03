from fastapi import APIRouter, Depends
from app.core.config import settings
from app.services.storage.json_repository import JsonRepository
from app.services.storage.data_loader import DataLoader
from app.models.schemas.champion_schemas import ChampionOut
from fastapi import HTTPException

router = APIRouter()

def get_loader():
    repo = JsonRepository(settings.data_dir)
    return DataLoader(repo)

@router.get("", response_model=list[ChampionOut])
def list_champions(loader: DataLoader = Depends(get_loader)):
    return loader.champions()

@router.get("/{champion_id}", response_model=ChampionOut)
def get_champion(champion_id: int, loader: DataLoader = Depends(get_loader)):
    for c in loader.champions():
        if c["id"] == champion_id:
            return c
    raise HTTPException(status_code=404, detail="Champion not found")