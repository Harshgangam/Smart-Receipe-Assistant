"""
backend/app/routers/substitutions.py

API router for Novelty 1: Substitution Graph & Knowledge Base Lookups
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, List, Optional

from backend.app.substitutions.graph import substitution_graph
from backend.app.substitutions.service import substitution_service

router = APIRouter(
    prefix="/substitutions",
    tags=["substitutions"],
)

class SubstitutionRequest(BaseModel):
    missing_ingredient: str
    pantry_ingredients: Optional[List[str]] = None
    dietary_preference: Optional[str] = None
    allergens: Optional[List[str]] = None
    context: Optional[str] = "general"

@router.post(
    "",
    summary="Get graph-based and curated ingredient substitutions",
)
def get_ingredient_substitutions(request: SubstitutionRequest):
    pantry = request.pantry_ingredients or []
    graph_res = substitution_graph.find_substitutes(
        missing_ingredient=request.missing_ingredient,
        pantry_items=pantry,
        context=request.context or "general",
        dietary_preference=request.dietary_preference,
        user_allergens=request.allergens,
    )
    raw_subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient=request.missing_ingredient,
        context=request.context or "general",
        dietary_preference=request.dietary_preference,
        allergens=request.allergens,
    )
    return {
        "missing_ingredient": request.missing_ingredient,
        "graph_substitution": graph_res,
        "curated_substitutions": [s.model_dump() for s in raw_subs],
    }
