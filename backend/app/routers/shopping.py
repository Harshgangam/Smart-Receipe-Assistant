"""
backend/app/routers/shopping.py

API router for Novelty 4: Micro-Shopping Optimizer & Pantry ROI
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List, Optional, Any

from backend.app.services.shopping_optimizer import shopping_optimizer, MicroShoppingPlan

router = APIRouter(
    prefix="/shopping",
    tags=["shopping"],
)

class OptimizeShoppingRequest(BaseModel):
    recipe_candidates: List[Dict[str, Any]]  # [{"title": str, "missing_ingredients": List[str]}]

@router.post(
    "/optimize",
    response_model=MicroShoppingPlan,
    summary="Generate optimized micro-shopping plan and Pantry ROI across candidate recipes",
)
def optimize_shopping(request: OptimizeShoppingRequest) -> MicroShoppingPlan:
    return shopping_optimizer.generate_shopping_plan(request.recipe_candidates)
