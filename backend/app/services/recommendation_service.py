from typing import Optional
from backend.app.config import settings
from backend.app.models.recommendation import PantryRequest, RecommendationResponse
from backend.app.recommendation.engine import RecommendationEngine


class RecommendationService:
    """Service layer orchestrating recommendation requests."""

    def __init__(self, engine: Optional[RecommendationEngine] = None):
        self.engine = engine or RecommendationEngine(
            sqlite_path=settings.SQLITE_INDEX_PATH,
            parquet_path=settings.PARQUET_PATH,
            ims_weight=settings.IMS_WEIGHT,
            pus_weight=settings.PUS_WEIGHT,
            candidate_limit=settings.CANDIDATE_POOL_LIMIT,
        )

    def get_recommendations(self, request: PantryRequest) -> RecommendationResponse:
        return self.engine.recommend(
            pantry_ingredients=request.pantry_ingredients,
            limit=request.limit,
            cuisine=request.cuisine,
            dietary_preference=request.dietary_preference,
            allergens=request.allergens,
            max_cooking_time_minutes=request.max_cooking_time_minutes,
            query_text=request.query_text,
            pantry_items_details=request.pantry_items_details,
        )


# Global service instance
recommendation_service = RecommendationService()
