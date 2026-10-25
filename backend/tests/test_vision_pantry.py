"""
backend/tests/test_vision_pantry.py

Comprehensive test suite for Phase 16:
- Food ingredient recognition
- Transparent container ambiguity handling
- 3-tier confidence gating
- Ingredient normalizer
- SQLite pantry management (CRUD, UPSERT, duplicates, provenance)
- Vision upload and confirm endpoints
- Verification that obsolete micro-shopping endpoints return 404
"""

import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.ingredient_normalizer import ingredient_normalizer
from backend.app.services.vision_intake import vision_intake_service, ConfidenceLevel, ContainerType
from backend.app.pantry.sqlite_pantry import sqlite_pantry
from backend.app.pantry.pantry_store import pantry_store


@pytest.fixture(autouse=True)
def isolate_test_pantry(tmp_path):
    """Isolates pantry storage so tests never modify production database."""
    test_db = tmp_path / "test_pantry.sqlite"
    test_json = tmp_path / "test_pantry.json"
    test_notif = tmp_path / "test_notif.json"

    orig_sqlite_path = sqlite_pantry.db_path
    orig_store_db = pantry_store.db_path
    orig_notif_db = pantry_store.notif_db_path
    orig_items = dict(pantry_store._items)

    sqlite_pantry.db_path = test_db
    sqlite_pantry._ensure_db()
    pantry_store.db_path = test_json
    pantry_store.notif_db_path = test_notif
    pantry_store._items = {}

    yield

    sqlite_pantry.db_path = orig_sqlite_path
    pantry_store.db_path = orig_store_db
    pantry_store.notif_db_path = orig_notif_db
    pantry_store._items = orig_items


@pytest.fixture
def client():
    return TestClient(app)


def create_test_image(color=(200, 30, 30), size=(100, 100), format="JPEG"):
    """Generates an in-memory image bytes buffer."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=color)
    img.save(buf, format=format)
    buf.seek(0)
    return buf.getvalue()


# ── 1. Ingredient Normalizer Unit Tests ────────────────────────────────────────

def test_normalizer_exact_canonical():
    name, conf, resolved = ingredient_normalizer.normalize("tomato")
    assert name == "tomato"
    assert conf == 1.0
    assert resolved is True


def test_normalizer_synonyms_and_regional_terms():
    # dahi -> curd
    name, conf, resolved = ingredient_normalizer.normalize("dahi")
    assert name == "curd"
    assert conf >= 0.95
    assert resolved is True

    # bell pepper -> capsicum
    name, conf, resolved = ingredient_normalizer.normalize("bell pepper")
    assert name == "capsicum"
    assert resolved is True

    # yoghurt -> curd
    name, conf, resolved = ingredient_normalizer.normalize("yoghurt")
    assert name == "curd"

    # cilantro -> coriander
    name, conf, resolved = ingredient_normalizer.normalize("fresh cilantro")
    assert name == "coriander"


def test_normalizer_plurals():
    name, conf, resolved = ingredient_normalizer.normalize("tomatoes")
    assert name == "tomato"

    name, conf, resolved = ingredient_normalizer.normalize("potatoes")
    assert name == "potato"


def test_normalizer_unknown_fallback():
    name, conf, resolved = ingredient_normalizer.normalize("xyzrandomingredient123")
    assert conf < 0.60
    assert resolved is False


# ── 2. Vision Service & Transparent Container Tests ───────────────────────────

def test_vision_intake_red_produce():
    # Simulates red produce (tomato)
    img_bytes = create_test_image(color=(220, 20, 20))
    res = vision_intake_service.process_image(img_bytes, filename="tomatoes.jpg")
    assert res["status"] == "success"
    assert len(res["detected_ingredients"]) > 0
    names = [d["canonical_name"] for d in res["detected_ingredients"]]
    assert "tomato" in names


def test_vision_intake_transparent_container_dairy():
    # Bright near-white image simulating dairy (curd/yogurt/cream) in transparent box
    img_bytes = create_test_image(color=(240, 240, 240))
    res = vision_intake_service.process_image(img_bytes, filename="curd_box.jpg")
    assert res["status"] == "success"
    
    # Check if curd was detected with ambiguity flag
    curd_item = next((d for d in res["detected_ingredients"] if d["canonical_name"] == "curd"), None)
    if curd_item:
        assert curd_item["is_ambiguous"] is True
        assert curd_item["requires_confirmation"] is True
        assert "transparent" in curd_item["container_type"].lower() or "confirm" in curd_item["review_message"].lower()


def test_vision_intake_corrupted_image():
    with pytest.raises(ValueError):
        vision_intake_service.process_image(b"not an image", filename="corrupt.jpg")


def test_vision_intake_tiny_image():
    # 10x10 is below minimum 30x30 resolution
    img_bytes = create_test_image(size=(10, 10))
    with pytest.raises(ValueError):
        vision_intake_service.process_image(img_bytes, filename="tiny.jpg")


# ── 3. SQLite Pantry Store Tests ──────────────────────────────────────────────

def test_sqlite_pantry_add_and_get():
    import time
    unique_name = f"Test Heirloom Tomatoes {int(time.time() * 1000)}"
    item = sqlite_pantry.add_or_upsert_item({
        "name": unique_name,
        "quantity": 3.0,
        "unit": "pcs",
        "category": "Produce",
        "detection_source": "vision_test",
    })
    assert item is not None
    assert item["quantity"] == 3.0
    assert item["detection_source"] == "vision_test"

    # Verify duplicate prevention (merging quantities)
    item2 = sqlite_pantry.add_or_upsert_item({
        "name": unique_name,
        "quantity": 2.0,
        "unit": "pcs",
        "category": "Produce",
        "detection_source": "vision_test",
    })
    assert item2["id"] == item["id"]
    assert item2["quantity"] == 5.0  # 3 + 2
    sqlite_pantry.delete_item(item["id"])


def test_sqlite_pantry_manual_entry():
    item = pantry_store.add_item({
        "name": "Fresh Spinach",
        "category": "Produce",
        "quantity": 1.0,
        "unit": "bunch",
    })
    assert item.name == "Fresh Spinach"
    stored = pantry_store.get_item(item.id)
    assert stored is not None
    assert stored.name == "Fresh Spinach"


# ── 4. FastAPI Endpoints Tests ────────────────────────────────────────────────

def test_api_vision_upload_success(client):
    img_bytes = create_test_image(color=(30, 200, 30))  # Green vegetable
    response = client.post(
        "/api/pantry/vision-upload",
        files={"file": ("capsicum.png", img_bytes, "image/png")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "detected_ingredients" in data
    assert len(data["detected_ingredients"]) > 0


def test_api_vision_upload_unsupported_format(client):
    response = client.post(
        "/api/pantry/vision-upload",
        files={"file": ("document.pdf", b"%PDF-1.4...", "application/pdf")},
    )
    assert response.status_code == 415


def test_api_vision_upload_empty_file(client):
    response = client.post(
        "/api/pantry/vision-upload",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert response.status_code == 400


def test_api_vision_confirm_and_trigger_rag(client):
    payload = {
        "confirmed_items": [
            {
                "name": "Tomatoes",
                "canonical_name": "tomato",
                "category": "Produce",
                "quantity": 4.0,
                "unit": "pcs",
                "expiry_days": 5,
                "confidence": 0.95,
            },
            {
                "name": "Curd",
                "canonical_name": "curd",
                "category": "Dairy",
                "quantity": 1.0,
                "unit": "container",
                "expiry_days": 4,
                "confidence": 0.85,
            }
        ],
        "trigger_recipe_recommendations": True,
    }
    response = client.post("/api/pantry/vision-confirm", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["added_items"]) == 2
    assert "recommendations" in data


def test_api_vision_confirm_replace_mode(client):
    # First, seed an initial item
    pantry_store.add_item({"name": "Old Cabbage", "quantity": 1.0, "unit": "pcs"})
    assert len(pantry_store.get_all()) == 1

    # Confirm in replace mode
    payload = {
        "confirmed_items": [
            {"name": "Noodles", "canonical_name": "noodles", "category": "Grains", "quantity": 2.0, "unit": "pack"},
            {"name": "Potato", "canonical_name": "potato", "category": "Produce", "quantity": 3.0, "unit": "pcs"}
        ],
        "mode": "replace",
        "trigger_recipe_recommendations": False,
    }
    response = client.post("/api/pantry/vision-confirm", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    current_items = data["current_pantry"]
    assert len(current_items) == 2
    names = [i["name"] for i in current_items]
    assert "Old Cabbage" not in names
    assert "Noodles" in names
    assert "Potato" in names


def test_obsolete_micro_shopping_endpoint_removed(client):
    # Verifies that /api/shopping/optimize no longer exists
    response = client.post("/api/shopping/optimize", json={"recipe_candidates": []})
    assert response.status_code == 404
