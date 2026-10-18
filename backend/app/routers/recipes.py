"""
backend/app/routers/recipes.py

API router for retrieving individual recipe details by ID.
"""

from fastapi import APIRouter, HTTPException, Query, status
from typing import List, Optional

from backend.app.assistant.context_assembler import context_assembler

router = APIRouter(
    prefix="/recipes",
    tags=["recipes"],
)

@router.get(
    "/{recipe_id}",
    summary="Get full recipe details by ID",
)
def get_recipe_by_id(recipe_id: int, pantry: Optional[List[str]] = Query(None)):
    ctx = context_assembler.assemble_context(recipe_id=recipe_id, pantry_ingredients=pantry)
    if not ctx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recipe with ID {recipe_id} not found.",
        )
    return ctx
