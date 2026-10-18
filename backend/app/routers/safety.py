"""
backend/app/routers/safety.py

API router for Novelty 2: Allergen Hard-Lock & Contextual RAG Audit
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from backend.app.safety.allergen_guard import allergen_guard, SafetyCheckResult

router = APIRouter(
    prefix="/safety",
    tags=["safety"],
)

class SafetyCheckRequest(BaseModel):
    recipe_id: int
    recipe_title: str
    ingredients: List[str]
    directions: List[str]
    allergens: Optional[List[str]] = None
    dietary_preference: Optional[str] = None

@router.post(
    "/check",
    response_model=SafetyCheckResult,
    summary="Screen recipe against deterministic allergen locks and RAG contextual audit",
)
def check_safety(request: SafetyCheckRequest) -> SafetyCheckResult:
    return allergen_guard.check_recipe_safety(
        recipe_id=request.recipe_id,
        recipe_title=request.recipe_title,
        ingredients=request.ingredients,
        directions=request.directions,
        user_allergens=request.allergens,
        user_diet=request.dietary_preference,
    )
