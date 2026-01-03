from fastapi import APIRouter, Depends, HTTPException
from app.core.config import settings
from app.services.storage.json_repository import JsonRepository
from app.services.storage.data_loader import DataLoader

router = APIRouter()

def get_loader():
    repo = JsonRepository(settings.data_dir)
    return DataLoader(repo)

@router.get("/draft-formats")
def get_draft_formats(loader: DataLoader = Depends(get_loader)):
    """
    Retourne le JSON complet des formats (flex/tournament).
    Le fichier attendu est: data/configs/draft_formats.json
    """
    try:
        return loader.draft_formats()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="draft_formats.json not found")

@router.get("/draft-formats/{format_key}")
def get_draft_format(format_key: str, loader: DataLoader = Depends(get_loader)):
    try:
        formats = loader.draft_formats()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="draft_formats.json not found")

    if format_key not in formats:
        raise HTTPException(status_code=404, detail=f"Unknown format: {format_key}")

    return formats[format_key]
