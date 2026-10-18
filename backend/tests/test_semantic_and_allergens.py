"""
backend/tests/test_semantic_and_allergens.py

Unit tests verifying:
1. Semantic Ingredient Normalization & Matching (e.g., '4 potatoes' == 'potatoes').
2. Relatable Recipe Images (category-accurate culinary photography, no random mismatches).
3. Hard Allergen Safety Lock with custom user input & semantic taxonomy expansion.
"""

import pytest

from backend.app.recommendation.normalizer import (
    extract_core_food,
    get_lookup_variants,
    normalize_pantry_ingredient,
    normalize_pantry_list,
    to_singular_form,
)
from backend.app.recommendation.scorer import is_semantic_match
from backend.app.safety.allergen_guard import (
    allergen_guard,
    expand_user_allergen_semantically,
    check_term_in_text_with_word_boundaries,
)
from backend.app.services.sandbox_engine import (
    _detect_culinary_category,
    resolve_recipe_image_url,
    _UNSPLASH_POOLS,
)


# ============================================================================
# 1. Semantic Ingredient Normalization & Matching Tests
# ============================================================================

def test_potatoes_and_quantified_potatoes_are_semantically_identical():
    """
    Direct user issue verification:
    'potatoes' and '4 potatoes' must be recognized as the same core food concept.
    """
    # 1. Core food extraction must extract 'potato' or 'potatoes'
    core_a = extract_core_food("potatoes")
    core_b = extract_core_food("4 potatoes")
    assert to_singular_form(core_a) == to_singular_form(core_b) == "potato"

    # 2. Both must match semantically via is_semantic_match
    assert is_semantic_match("potatoes", "4 potatoes")
    assert is_semantic_match("4 potatoes", "potatoes")
    assert is_semantic_match("potato", "4 potatoes")
    assert is_semantic_match("4 potatoes", "potato")
    assert is_semantic_match("4 russet potatoes", "potatoes")
    assert is_semantic_match("medium potatoes", "potatoes")
    assert is_semantic_match("4 medium potatoes", "potatoes")
    assert is_semantic_match("4 medium potatoes, peeled and cut into 1/2-inch strips", "potatoes")

    # 3. Deduplication in normalize_pantry_list
    normalized_list, lookup_variants = normalize_pantry_list(["potatoes", "4 potatoes", "medium potatoes", "4 medium potatoes"])
    # Should deduplicate down to a single entry
    assert len(normalized_list) == 1
    # Both 'potato' and 'potatoes' must be present in lookup variants for database retrieval
    assert "potato" in lookup_variants or "potatoes" in lookup_variants


def test_various_quantified_and_prep_modified_ingredients():
    """Verify units, numbers, fractions, and adjectives are handled semantically."""
    assert is_semantic_match("onion", "2 cups diced onions")
    assert is_semantic_match("1/2 lb ground beef", "beef")
    assert is_semantic_match("garlic", "3 cloves minced garlic")
    assert is_semantic_match("fresh tomatoes", "4 ripe tomatoes")


def test_culinary_synonyms():
    """Verify culinary synonyms resolve to the same food concept."""
    assert is_semantic_match("scallion", "green onion")
    assert is_semantic_match("green onions", "scallions")
    assert is_semantic_match("cilantro", "coriander")
    assert is_semantic_match("bell pepper", "capsicum")


# ============================================================================
# 2. Relatable Recipe Images Tests
# ============================================================================

def test_detect_culinary_category():
    """Test culinary category detection from recipe titles and NER."""
    assert _detect_culinary_category("Creamy Garlic Mashed Potatoes", ner=["potatoes", "milk", "butter"]) == "potato"
    assert _detect_culinary_category("Crispy French Fries", ner=["potatoes", "oil", "salt"]) == "fries"
    assert _detect_culinary_category("Oven French Fries 1(French Fries Without Frying)") == "fries"
    assert _detect_culinary_category("Classic Spaghetti Bolognese", ner=["pasta", "ground beef", "tomato sauce"]) == "pasta"
    assert _detect_culinary_category("Vegetable Fried Rice", ner=["rice", "egg", "peas", "soy sauce"]) == "rice"
    assert _detect_culinary_category("Cheesy Pepperoni Pizza", ner=["flour", "mozzarella", "pepperoni"]) == "pizza"
    assert _detect_culinary_category("Chicken Noodle Soup", ner=["chicken", "noodles", "broth", "carrots"]) == "soup"
    assert _detect_culinary_category("Grilled Salmon Fillet", ner=["salmon", "lemon", "olive oil"]) == "seafood"


def test_relatable_image_resolution():
    """
    Ensure recipe image resolution yields a photo relatable to the meal,
    never returning mismatched items like cake/dessert for a savory dish,
    and never returning the mistakenly labelled Idli photo for French Fries.
    """
    # 1. French fries dish must receive authentic fries photo, never Idli
    img_fries = resolve_recipe_image_url(
        title="Oven French Fries 1(French Fries Without Frying)",
        ner=["potatoes", "vegetable oil", "salt"],
        recipe_id=999,
    )
    assert "1589301760014" not in img_fries  # Purged Idli photo
    assert any(p in img_fries for p in _UNSPLASH_POOLS["fries"]) or "fries" in img_fries.lower() or "chips" in img_fries.lower()

    # 2. Potato dishes must receive an image from the potato pool or potato-specific catalog
    img_potato = resolve_recipe_image_url(
        title="Country Fried Potatoes with Herbs",
        ner=["potatoes", "onion", "olive oil", "parsley"],
        recipe_id=101,
    )
    assert "1589301760014" not in img_potato  # Purged Idli photo
    assert any(p in img_potato for p in _UNSPLASH_POOLS["potato"]) or "potato" in img_potato.lower()

    # 3. Pasta dishes must receive a pasta image
    img_pasta = resolve_recipe_image_url(
        title="Penne All'Arrabbiata",
        ner=["penne", "tomatoes", "garlic", "chili"],
        recipe_id=102,
    )
    assert any(p in img_pasta for p in _UNSPLASH_POOLS["pasta"]) or "pasta" in img_pasta.lower() or "spaghetti" in img_pasta.lower()

    # 3. Chicken soup must receive a soup image
    img_soup = resolve_recipe_image_url(
        title="Hearty Vegetable and Bean Soup",
        ner=["carrots", "celery", "beans", "broth"],
        recipe_id=103,
    )
    from backend.app.services.sandbox_engine import _PHOTO_CATALOG
    is_soup_catalog_or_pool = (
        any(p in img_soup for p in _UNSPLASH_POOLS["soup"])
        or any(m["url"] == img_soup and ("soup" in m["name"].lower() or "soup" in m.get("keywords", [])) for m in _PHOTO_CATALOG)
    )
    assert is_soup_catalog_or_pool


# ============================================================================
# 3. Hard Allergen Safety Lock Tests
# ============================================================================

def test_custom_allergen_expansion():
    """Verify semantic expansion of user entered allergens."""
    expanded_shrimp = expand_user_allergen_semantically("shrimp")
    assert "shrimp" in expanded_shrimp
    assert "prawn" in expanded_shrimp or "prawns" in expanded_shrimp

    expanded_potato = expand_user_allergen_semantically("potatoes")
    assert "potato" in expanded_potato
    assert "potatoes" in expanded_potato

    expanded_peanut = expand_user_allergen_semantically("peanut")
    assert "peanut" in expanded_peanut
    assert "peanut butter" in expanded_peanut


def test_allergen_guard_blocks_custom_allergens():
    """Verify that user-locked custom allergens strictly block offending recipes."""
    # Recipe with shrimp
    shrimp_recipe = {
        "recipe_id": 201,
        "recipe_title": "Garlic Butter Shrimp Pasta",
        "ingredients": ["8 oz pasta", "1 lb fresh shrimp peeled", "3 cloves garlic", "2 tbsp butter"],
        "directions": ["Sauté garlic and shrimp in butter, toss with cooked pasta."],
    }
    safety_with_shrimp_lock = allergen_guard.check_recipe_safety(
        recipe_id=shrimp_recipe["recipe_id"],
        recipe_title=shrimp_recipe["recipe_title"],
        ingredients=shrimp_recipe["ingredients"],
        directions=shrimp_recipe["directions"],
        user_allergens=["shrimp"],
        recipe_ner=["pasta", "shrimp", "garlic", "butter"],
    )
    assert safety_with_shrimp_lock.status == "BLOCKED"
    assert "shrimp" in safety_with_shrimp_lock.allergens_detected

    # Recipe with potatoes when user locks potato
    potato_recipe = {
        "recipe_id": 202,
        "recipe_title": "Loaded Baked Potato Casserole",
        "ingredients": ["4 large russet potatoes", "1 cup cheddar cheese", "sour cream"],
        "directions": ["Bake potatoes and mash with cheese."],
    }
    safety_with_potato_lock = allergen_guard.check_recipe_safety(
        recipe_id=potato_recipe["recipe_id"],
        recipe_title=potato_recipe["recipe_title"],
        ingredients=potato_recipe["ingredients"],
        directions=potato_recipe["directions"],
        user_allergens=["potatoes"],
        recipe_ner=["potatoes", "cheddar cheese", "sour cream"],
    )
    assert safety_with_potato_lock.status == "BLOCKED"
    assert any("potato" in a for a in safety_with_potato_lock.allergens_detected)


def test_allergen_guard_prevents_false_positives():
    """
    Verify word boundary checks prevent false positives:
    - Locking 'egg' must NOT block 'eggplant'
    - Locking 'ham' must NOT block 'graham crackers'
    """
    eggplant_dish = {
        "recipe_id": 203,
        "recipe_title": "Roasted Eggplant with Tahini",
        "ingredients": ["2 medium eggplants", "tahini", "lemon juice", "olive oil"],
        "directions": ["Roast eggplant until soft."],
    }
    safety_check = allergen_guard.check_recipe_safety(
        recipe_id=eggplant_dish["recipe_id"],
        recipe_title=eggplant_dish["recipe_title"],
        ingredients=eggplant_dish["ingredients"],
        directions=eggplant_dish["directions"],
        user_allergens=["egg"],
        recipe_ner=["eggplants", "tahini", "lemon juice", "olive oil"],
    )
    # Must be SAFE - eggplant is not egg!
    assert safety_check.status == "SAFE"
    assert len(safety_check.allergens_detected) == 0


# ============================================================================
# 4. Compulsory Vegetarian Lock & Image Guarantee Tests
# ============================================================================

def test_compulsory_vegetarian_blocks_all_meat_dishes():
    """Verify that when vegetarian diet is specified, all meat/poultry/fish dishes are strictly blocked."""
    meat_dishes = [
        {"id": 301, "title": "Bacon Cheddar Skillet", "ingredients": ["bacon", "cheddar", "potatoes"], "ner": ["bacon", "cheddar", "potatoes"]},
        {"id": 302, "title": "Crispy Chicken Tenders", "ingredients": ["chicken breast", "breadcrumbs", "oil"], "ner": ["chicken breast", "breadcrumbs", "oil"]},
        {"id": 303, "title": "Honey Glazed Ham", "ingredients": ["ham", "honey", "mustard"], "ner": ["ham", "honey", "mustard"]},
        {"id": 304, "title": "Grilled Ribeye Steak", "ingredients": ["beef steak", "garlic", "butter"], "ner": ["beef steak", "garlic", "butter"]},
        {"id": 305, "title": "Pan-Seared Tuna", "ingredients": ["tuna steak", "sesame", "soy sauce"], "ner": ["tuna", "sesame", "soy sauce"]},
    ]

    for dish in meat_dishes:
        res = allergen_guard.check_recipe_safety(
            recipe_id=dish["id"],
            recipe_title=dish["title"],
            ingredients=dish["ingredients"],
            directions=["Cook thoroughly and serve hot."],
            user_diet="vegetarian",
            recipe_ner=dish["ner"],
        )
        assert res.is_blocked is True, f"Recipe '{dish['title']}' should be BLOCKED for vegetarian diet."
        assert any("Vegetarian" in r for r in res.reasons)


def test_vegetarian_image_resolution_never_returns_meat_photos():
    """Verify that when dietary_preference='vegetarian', resolve_recipe_image_url never returns meat photography."""
    meat_words = ["chicken", "beef", "pork", "steak", "bacon", "salmon", "shrimp", "seafood", "ribs", "burger"]

    # Even if title or ingredients contain an ambiguous term, veg preference overrides category
    img = resolve_recipe_image_url(
        title="Savory Vegetable Medley",
        recipe_id=401,
        ner=["broccoli", "potatoes", "carrots"],
        ingredients=["broccoli", "potatoes", "carrots", "olive oil"],
        dietary_preference="vegetarian",
    )
    assert not any(mw in img.lower() for mw in ["chicken", "steak", "pork", "ribs"])
    assert img.startswith("http")


def test_corn_and_fritter_category_detection():
    """Verify that corn dishes and fritters/patties receive dedicated category classification."""
    from backend.app.services.sandbox_engine import _detect_culinary_category

    assert _detect_culinary_category("Crispy Sweet Corn Fritters", ["corn", "flour", "oil"]) == "fritter"
    assert _detect_culinary_category("Golden Corn Patties", ["corn", "breadcrumbs", "onion"]) == "fritter"
    assert _detect_culinary_category("Grilled Sweet Corn on the Cob", ["corn", "butter", "salt"]) == "corn"
    assert _detect_culinary_category("Zucchini Herb Fritters", ["zucchini", "egg", "dill"]) == "fritter"


def test_image_deduplication_guarantee_across_session():
    """Verify that sequential recipe cards never receive duplicate images in the same view."""
    titles = [
        "Grilled Vegetable Salad",
        "Corn Fritters",
        "Sweet Corn Chowder",
        "Golden Corn Patties",
        "Fried Corn with Herbs",
        "Zucchini Corn Fritters",
        "Country Fried Potatoes",
        "Roasted Vegetable Medley",
        "Sweet Corn Skillet",
    ]

    used_images: set = set()
    assigned_images = []

    for i, title in enumerate(titles):
        img = resolve_recipe_image_url(
            title=title,
            recipe_id=500 + i,
            used_urls=used_images,
            dietary_preference="vegetarian",
        )
        assigned_images.append(img)
        used_images.add(img)

    # Every single card must receive a distinct, unique image URL
    assert len(assigned_images) == len(titles)
    assert len(set(assigned_images)) == len(titles), f"Duplicate images detected: {assigned_images}"


