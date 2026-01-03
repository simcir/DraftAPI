from fastapi import APIRouter, Depends

from app.core.config import settings
from app.services.storage.json_repository import JsonRepository
from app.services.storage.data_loader import DataLoader
from app.services.scoring.scoring_engine import build_recommendations
from app.models.schemas.recommendation_schemas import (
    DraftRecommendationRequest,
    DraftRecommendationResponse,
)

router = APIRouter()

def get_loader():
    repo = JsonRepository(settings.data_dir)
    return DataLoader(repo)

@router.post("/recommendations", response_model=DraftRecommendationResponse)
def recommend(payload: DraftRecommendationRequest, loader: DataLoader = Depends(get_loader)):
    recommendations = build_recommendations(payload, loader)
    return DraftRecommendationResponse(recommendations=recommendations)
