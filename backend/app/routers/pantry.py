from typing import Any, Dict, List, Optional
import json
from pathlib import Path
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from backend.app.pantry.pantry_store import PantryItem, pantry_store
from backend.app.models.recommendation import PantryCookRequest, PantryScanResponse
from backend.app.config import settings

router = APIRouter(prefix="/pantry", tags=["pantry"])

# ── Load FoodKeeper data once at startup ──────────────────────────────────────
_FOODKEEPER_PATH = settings.PROCESSED_DATA_DIR / "foodkeeper.json"
_foodkeeper_products: List[Dict] = []

def _load_foodkeeper():
    global _foodkeeper_products
    if _FOODKEEPER_PATH.exists() and not _foodkeeper_products:
        raw = json.loads(_FOODKEEPER_PATH.read_text(encoding="utf-8"))
        for sheet in raw.get("sheets", []):
            if sheet.get("name") == "Product":
                for row in sheet.get("data", []):
                    if isinstance(row, list):
                        # Each row is a list of single-key dicts — merge them all
                        merged: Dict = {}
                        for field in row:
                            if isinstance(field, dict):
                                merged.update(field)
                        _foodkeeper_products.append(merged)
                    elif isinstance(row, dict):
                        _foodkeeper_products.append(row)
                break

_load_foodkeeper()


def _metric_to_days(value: float, metric: str) -> int:
    """Convert FoodKeeper metric+value to integer days."""
    metric = (metric or "").lower()
    if "day" in metric:
        return int(value)
    if "week" in metric:
        return int(value * 7)
    if "month" in metric:
        return int(value * 30)
    if "year" in metric:
        return int(value * 365)
    return int(value)  # fallback: treat raw number as days


def _lookup_shelf_life(ingredient: str) -> int:
    """Fuzzy-match ingredient against FoodKeeper products → return shelf life days."""
    query = ingredient.lower().strip()
    best_days = None
    best_score = 0

    for product in _foodkeeper_products:
        name = str(product.get("Name", "")).lower()
        keywords = str(product.get("Keywords", "")).lower()
        combined = f"{name} {keywords}"

        # Score: exact name match > keyword match > partial
        score = 0
        if query == name:
            score = 100
        elif query in name or name in query:
            score = 80
        elif any(q in combined for q in query.split()):
            score = 50

        if score > best_score:
            best_score = score
            # Prefer DOP_Refrigerate (from date of purchase), then Refrigerate
            for min_key, max_key, metric_key in [
                ("DOP_Refrigerate_Min", "DOP_Refrigerate_Max", "DOP_Refrigerate_Metric"),
                ("Refrigerate_Min", "Refrigerate_Max", "Refrigerate_Metric"),
                ("DOP_Pantry_Min", "DOP_Pantry_Max", "DOP_Pantry_Metric"),
            ]:
                val = product.get(max_key) or product.get(min_key)
                metric = product.get(metric_key, "")
                if val and metric and "not recommended" not in str(metric).lower() and "use-by" not in str(metric).lower():
                    best_days = _metric_to_days(float(val), metric)
                    break

    # Fallback defaults by common category keywords
    if best_days is None:
        fallbacks = {
            "meat": 3, "chicken": 2, "fish": 2, "seafood": 2,
            "milk": 7, "dairy": 10, "cheese": 14, "egg": 21,
            "vegetable": 5, "fruit": 5, "bread": 5,
            "grain": 180, "pasta": 180, "rice": 365, "can": 365,
        }
        for kw, days in fallbacks.items():
            if kw in query:
                best_days = days
                break
        if best_days is None:
            best_days = 7  # generic default

    return best_days


class PantryItemCreate(BaseModel):
    name: str
    category: Optional[str] = "General"
    quantity: Optional[float] = 1.0
    unit: Optional[str] = "pcs"
    expiry_days: Optional[int] = 7
    storage_location: Optional[str] = "pantry"


class PantryItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    expiry_days: Optional[int] = None
    storage_location: Optional[str] = None
    status: Optional[str] = None


@router.get("", response_model=List[PantryItem])
@router.get("/items", response_model=List[PantryItem])
def get_pantry_items(status_filter: Optional[str] = "available"):
    """
    Get current user pantry items with expiry risk levels and status.
    """
    return pantry_store.get_all(status=status_filter)


@router.post("/items", response_model=PantryItem, status_code=status.HTTP_201_CREATED)
def add_pantry_item(item_data: PantryItemCreate):
    """
    Add a new ingredient item to the user's dynamic pantry inventory.
    """
    new_item = pantry_store.add_item(item_data.model_dump())
    return new_item


@router.put("/items/{item_id}", response_model=PantryItem)
def update_pantry_item(item_id: str, updates: PantryItemUpdate):
    """
    Update quantity, expiry, or details of a pantry item.
    """
    updated = pantry_store.update_item(item_id, updates.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Pantry item not found")
    return updated


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_pantry_item(item_id: str):
    """
    Remove an ingredient from the user's pantry.
    """
    success = pantry_store.delete_item(item_id)
    if not success:
        raise HTTPException(status_code=404, detail="Pantry item not found")
    return None


@router.delete("/items", status_code=status.HTTP_204_NO_CONTENT)
@router.delete("/clear", status_code=status.HTTP_204_NO_CONTENT)
def clear_all_pantry_items():
    """
    Clear all ingredients from the user's pantry.
    """
    pantry_store.clear_all()
    return None


@router.post("/cook")
def record_cooking_feedback(req: PantryCookRequest):
    """
    Pantry Feedback Loop: Updates the pantry database after the user cooks a recipe,
    deducting consumed quantities and marking depleted items as consumed.
    """
    consumed_items = pantry_store.cook_recipe(req.recipe_ner, req.recipe_title)
    return {
        "status": "success",
        "recipe_cooked": req.recipe_title,
        "ingredients_deducted": consumed_items,
        "message": f"Successfully updated pantry after cooking '{req.recipe_title}'. Deducted {len(consumed_items)} pantry ingredients.",
        "current_pantry_state": pantry_store.get_all(status="available"),
    }

@router.get("/notifications")
def get_notifications():
    """
    Get all user notifications (expiries, cooking events).
    """
    return pantry_store.get_notifications()

@router.post("/notifications/read")
def mark_notifications_read():
    """
    Mark all unread notifications as read.
    """
    pantry_store.mark_notifications_read()
    return {"status": "success"}


@router.post("/scan-image", response_model=PantryScanResponse)
def scan_pantry_image():
    """
    Snap Your Pantry & OCR Expiry Detection: Simulates multi-modal computer vision
    object detection and OCR date extraction from a uploaded kitchen/fridge photo.
    """
    detected = [
        {"name": "Tomatoes", "category": "Produce", "quantity": 3.0, "unit": "pcs", "confidence": 0.94},
        {"name": "Milk Carton", "category": "Dairy", "quantity": 1.0, "unit": "liter", "confidence": 0.91},
        {"name": "Fresh Spinach", "category": "Produce", "quantity": 1.0, "unit": "pack", "confidence": 0.88},
        {"name": "Cheddar Cheese", "category": "Dairy", "quantity": 200.0, "unit": "g", "confidence": 0.85},
    ]

    dates = [
        {"item": "Milk Carton", "ocr_expiry_date": "2026-09-03", "expiry_days": 2, "confidence": "high"},
        {"item": "Cheddar Cheese", "ocr_expiry_date": "2026-09-07", "expiry_days": 6, "confidence": "medium"},
    ]

    # Automatically seed into pantry store
    for item in detected:
        pantry_store.add_item({
            "name": item["name"],
            "category": item["category"],
            "quantity": item["quantity"],
            "unit": item["unit"],
            "expiry_days": 2 if "Milk" in item["name"] else 4,
        })

    return PantryScanResponse(
        detected_ingredients=detected,
        ocr_extracted_dates=dates,
        scan_summary="Vision and OCR pipeline successfully identified 4 ingredients and 2 expiry dates from the image. Pantry items updated!",
    )


@router.get("/shelf-life/{ingredient}")
def get_shelf_life(ingredient: str):
    """
    FoodKeeper Shelf-Life Lookup: Returns base shelf life in days for an ingredient.
    Used by the frontend Freshness Buttons to auto-calculate expiry dates.
    - 🟢 Fresh       → 100% of base_shelf_life_days
    - 🟡 Few days old → 50% of base_shelf_life_days
    - 🔴 Use immediately → always 1 day
    """
    days = _lookup_shelf_life(ingredient)
    return {
        "ingredient": ingredient,
        "base_shelf_life_days": days,
        "fresh_days": days,
        "few_days_old_days": max(1, days // 2),
        "use_immediately_days": 1,
    }
