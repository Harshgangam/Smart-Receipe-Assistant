from typing import Any, Dict, List, Optional
import json
from pathlib import Path
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from backend.app.pantry.pantry_store import PantryItem, pantry_store
from backend.app.models.recommendation import PantryCookRequest, PantryScanResponse, PantryRequest
from backend.app.config import settings
from backend.app.services.vision_intake import vision_intake_service

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
    return int(value)


def _lookup_shelf_life(ingredient: str) -> int:
    """Fuzzy-match ingredient against FoodKeeper products → return shelf life days."""
    query = ingredient.lower().strip()
    best_days = None
    best_score = 0

    for product in _foodkeeper_products:
        name = str(product.get("Name", "")).lower()
        keywords = str(product.get("Keywords", "")).lower()
        combined = f"{name} {keywords}"

        score = 0
        if query == name:
            score = 100
        elif query in name or name in query:
            score = 80
        elif any(q in combined for q in query.split()):
            score = 50

        if score > best_score:
            best_score = score
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
            best_days = 7

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


class VisionConfirmItem(BaseModel):
    name: str
    canonical_name: Optional[str] = None
    category: Optional[str] = "General"
    quantity: Optional[float] = 1.0
    unit: Optional[str] = "pcs"
    expiry_days: Optional[int] = 7
    storage_location: Optional[str] = "pantry"
    confidence: Optional[float] = 1.0


class VisionConfirmRequest(BaseModel):
    confirmed_items: List[VisionConfirmItem]
    trigger_recipe_recommendations: bool = True
    mode: Optional[str] = "replace"  # "replace" (default) or "append"


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


# ── Vision-Powered Pantry Intake Endpoints ────────────────────────────────────

MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}


@router.post("/vision-upload")
async def vision_upload_image(file: UploadFile = File(...)):
    """
    Phase 8 & 12: Computer Vision Food Ingredient Recognition & Intake
    Accepts an uploaded photograph of kitchen countertop, fridge, or transparent container.
    Returns structured detections with confidence levels, container context, and confirmation flags.
    """
    # 1. Validate file existence and content type
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected for upload.")

    content_type = (file.content_type or "").lower()
    file_ext = Path(file.filename).suffix.lower()
    
    if content_type not in ALLOWED_CONTENT_TYPES and file_ext not in {".jpg", ".jpeg", ".png", ".webp"}:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type '{content_type}'. Please upload a JPEG, PNG, or WebP image."
        )

    # 2. Read and validate file size
    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Uploaded image is too large ({len(contents) / (1024*1024):.1f} MB). Maximum allowed size is 10 MB."
        )
    if len(contents) < 100:
        raise HTTPException(status_code=400, detail="Uploaded file is empty or corrupted.")

    # 3. Process with Computer Vision Service
    try:
        result = vision_intake_service.process_image(contents, filename=file.filename)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Vision processing error: {str(e)}")


@router.post("/vision-confirm")
def vision_confirm_pantry_updates(req: VisionConfirmRequest):
    """
    Phase 5 & 6: Commits user-approved vision detections to the SQLite pantry
    and immediately triggers updated recipe recommendations.
    """
    if not req.confirmed_items:
        raise HTTPException(status_code=400, detail="No confirmed items provided.")

    # In replace mode, wipe existing items so pantry matches only the newly scanned image
    if req.mode == "replace":
        pantry_store.clear_all()

    added_items = []
    for item in req.confirmed_items:
        expiry = item.expiry_days or _lookup_shelf_life(item.name)
        new_entry = pantry_store.add_item({
            "name": item.name,
            "normalized_name": item.canonical_name,
            "category": item.category or "General",
            "quantity": float(item.quantity or 1.0),
            "unit": item.unit or "pcs",
            "expiry_days": expiry,
            "storage_location": item.storage_location or "pantry",
            "detection_source": "vision_user_confirmed",
            "confidence": float(item.confidence or 1.0),
        })
        added_items.append(new_entry)

    # Trigger updated recipe recommendations
    recommendations_result = None
    if req.trigger_recipe_recommendations:
        try:
            from backend.app.services.recommendation_service import recommendation_service
            current_pantry = [item.name for item in pantry_store.get_all(status="available")]
            rec_request = PantryRequest(pantry_ingredients=current_pantry)
            recommendations_result = recommendation_service.get_recommendations(rec_request)
        except Exception as e:
            recommendations_result = {"warning": f"Recipe recommendation refresh skipped: {e}"}

    return {
        "status": "success",
        "message": f"Successfully updated pantry with {len(added_items)} verified ingredient(s).",
        "added_items": added_items,
        "current_pantry": pantry_store.get_all(status="available"),
        "recommendations": recommendations_result,
    }


@router.post("/scan-image")
async def scan_pantry_image_alias(file: Optional[UploadFile] = None):
    """
    Backward-compatible alias for Snap Your Pantry image scanner.
    Delegates to full vision_upload_image if file uploaded, or provides default scan.
    """
    if file:
        return await vision_upload_image(file)
    
    # Default demo fallback
    return {
        "detected_ingredients": [
            {"name": "Tomatoes", "canonical_name": "tomato", "confidence": 0.94, "confidence_level": "HIGH", "estimated_count": 3, "quantity_unit": "pieces", "requires_confirmation": False},
            {"name": "Curd", "canonical_name": "curd", "confidence": 0.74, "confidence_level": "MEDIUM", "estimated_count": None, "quantity_unit": None, "is_ambiguous": True, "requires_confirmation": True, "review_message": "Possible match: Curd in transparent container. Please confirm."}
        ]
    }


@router.get("/shelf-life/{ingredient}")
def get_shelf_life(ingredient: str):
    """
    FoodKeeper Shelf-Life Lookup: Returns base shelf life in days for an ingredient.
    """
    days = _lookup_shelf_life(ingredient)
    return {
        "ingredient": ingredient,
        "base_shelf_life_days": days,
        "fresh_days": days,
        "few_days_old_days": max(1, days // 2),
        "use_immediately_days": 1,
    }
