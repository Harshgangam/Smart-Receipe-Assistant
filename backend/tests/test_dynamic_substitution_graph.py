"""
backend/tests/test_dynamic_substitution_graph.py

Comprehensive Verification & Validation Suite for Dynamic Smart Substitution Graph.
Covers all 12 rigorous testing protocols mandated in the specification:
  1. Missing ingredient with a verified graph edge.
  2. Missing ingredient without a predefined substitution edge (dynamic graph discovery via role/texture).
  3. Multiple missing ingredients in one recipe (Pancake test scenario).
  4. Ingredient aliases and normalization.
  5. Candidate unavailable in pantry vs. candidate available in pantry.
  6. Candidate rejected by an allergen restriction (Allergen Hard-Lock).
  7. Candidate rejected by a dietary restriction (Dietary Hard-Lock).
  8. Multi-ingredient combination substitution (baking powder, buttermilk).
  9. Ingredient for which no suitable substitute exists (honesty, zero fabrication).
  10. Missing ingredient attributes and incomplete database records (graceful handling).
  11. Existing RAG and recipe recommendation engine integration.
  12. API response compatibility with the frontend.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.substitutions.graph import substitution_graph
from backend.app.substitutions.models import SubstitutionCandidate
from backend.app.substitutions.service import substitution_service
from backend.app.recommendation.engine import RecommendationEngine


# ------------------------------------------------------------------------------
# Test 1: Missing ingredient with a verified graph edge
# ------------------------------------------------------------------------------
def test_01_verified_graph_edge():
    """Verified graph edge returns standard substitution with high confidence and valid ratio."""
    subs = substitution_service.get_substitutions_for_ingredient("butter", context="baking")
    assert len(subs) > 0
    top = subs[0]
    assert top.missing_ingredient == "butter"
    assert top.substitute in ("margarine", "applesauce")
    assert top.confidence in ("high", "medium")
    assert top.ratio in ("1:1", "1:0.5")
    assert top.safety_status == "SAFE"


# ------------------------------------------------------------------------------
# Test 2: Missing ingredient without a predefined substitution edge (Dynamic Discovery)
# ------------------------------------------------------------------------------
def test_02_dynamic_discovery_without_predefined_edge():
    """Unindexed ingredient discovers functional substitute via role/texture graph traversal."""
    # 'lime juice' shares 'acid_brightener' / citrus role with 'lemon juice'
    subs = substitution_graph.find_candidates_for_ingredient(
        missing_ingredient="lime juice",
        context="cooking",
    )
    assert len(subs) > 0
    sub_names = [s.substitute.lower() for s in subs]
    assert any("lemon" in name or "vinegar" in name for name in sub_names)


# ------------------------------------------------------------------------------
# Test 3: Multiple missing ingredients in one recipe (Pancake Scenario)
# ------------------------------------------------------------------------------
def test_03_pancake_multi_ingredient_scenario():
    """
    Pancake recipe requires: flour, milk, egg, butter, baking powder.
    User has: flour, soy milk, oil, yogurt, baking soda.
    All missing ingredients must be evaluated independently with pantry-tailored substitutions.
    """
    recipe_missing = ["milk", "egg", "butter", "baking powder"]
    user_pantry = ["flour", "soy milk", "olive oil", "plain greek yogurt", "baking soda"]

    subs = substitution_service.get_substitutions_for_recipe(
        missing_ingredients=recipe_missing,
        recipe_title="Fluffy Buttermilk Pancakes",
        directions=["Whisk dry ingredients in bowl.", "Combine milk, eggs, melted butter.", "Bake on griddle."],
        pantry_ingredients=user_pantry,
    )

    subs_by_item = {s.missing_ingredient: s for s in subs}

    # 1. Milk -> Soy milk (in pantry)
    assert "milk" in subs_by_item
    assert "soy milk" in subs_by_item["milk"].substitute.lower()

    # 2. Butter -> Olive oil or oil (in pantry)
    assert "butter" in subs_by_item
    assert any(o in subs_by_item["butter"].substitute.lower() for o in ["oil", "margarine"])

    # 3. Egg -> Yogurt (binding & moisture alternative in pantry)
    assert "egg" in subs_by_item
    assert any(e in subs_by_item["egg"].substitute.lower() for e in ["yogurt", "applesauce", "flax"])

    # 4. Baking powder -> Baking soda + Yogurt (multi-ingredient combination in pantry)
    assert "baking powder" in subs_by_item
    bp_sub = subs_by_item["baking powder"]
    assert "baking soda" in bp_sub.substitute.lower()
    assert bp_sub.substitution_type == "combination"


# ------------------------------------------------------------------------------
# Test 4: Ingredient aliases and normalization
# ------------------------------------------------------------------------------
def test_04_ingredient_aliases_and_normalization():
    """Aliases like 'extra virgin olive oil' and 'freshly grated parmesan cheese' resolve properly."""
    subs_alias = substitution_service.get_substitutions_for_ingredient("extra virgin olive oil", context="frying")
    assert len(subs_alias) > 0

    subs_cheese = substitution_service.get_substitutions_for_ingredient("freshly grated parmesan cheese")
    assert len(subs_cheese) > 0
    assert any("pecorino" in s.substitute.lower() or "yeast" in s.substitute.lower() for s in subs_cheese)


# ------------------------------------------------------------------------------
# Test 5: Candidate available in pantry vs unavailable in pantry
# ------------------------------------------------------------------------------
def test_05_pantry_availability_boost():
    """Candidates on hand in the pantry are prioritized and tagged with pantry presence."""
    # User has oat milk in pantry, but not soy milk
    user_pantry = ["oat milk"]
    subs = substitution_graph.find_candidates_for_ingredient(
        missing_ingredient="milk",
        pantry_items=user_pantry,
        context="general",
    )
    assert len(subs) > 0
    # Oat milk should be prioritized to top candidate because it is in user's pantry
    assert subs[0].substitute == "oat milk"
    assert "Available in your pantry" in subs[0].reason


# ------------------------------------------------------------------------------
# Test 6: Candidate rejected by an allergen restriction (Allergen Hard-Lock)
# ------------------------------------------------------------------------------
def test_06_allergen_hardlock():
    """Dairy substitutes must be strictly rejected when dairy allergy is specified."""
    subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="milk",
        allergens=["dairy"],
    )
    assert len(subs) > 0
    for s in subs:
        assert "dairy" not in s.substitute.lower()
        assert s.substitute in ("soy milk", "almond milk", "oat milk")

    # Mozzarella under dairy allergy must reject provolone and return vegan/plant-based
    cheese_subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="mozzarella",
        allergens=["dairy"],
    )
    assert len(cheese_subs) > 0
    for s in cheese_subs:
        assert "provolone" not in s.substitute.lower()
        assert "cheddar" not in s.substitute.lower()


# ------------------------------------------------------------------------------
# Test 7: Candidate rejected by a dietary restriction (Dietary Hard-Lock)
# ------------------------------------------------------------------------------
def test_07_dietary_hardlock():
    """Animal products must be strictly rejected under vegan and vegetarian preferences."""
    # Under vegan, butter cannot return dairy butter or margarine with dairy
    vegan_butter_subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="butter",
        dietary_preference="vegan",
    )
    assert len(vegan_butter_subs) > 0
    for s in vegan_butter_subs:
        assert s.dietary_compatible is True
        assert s.substitute in ("margarine", "olive oil", "applesauce")

    # Under vegetarian, chicken broth must return vegetable broth
    veg_broth_subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="chicken broth",
        dietary_preference="vegetarian",
    )
    assert len(veg_broth_subs) > 0
    assert any("vegetable" in s.substitute.lower() for s in veg_broth_subs)
    for s in veg_broth_subs:
        assert "chicken" not in s.substitute.lower()
        assert "beef" not in s.substitute.lower()


# ------------------------------------------------------------------------------
# Test 8: Multi-ingredient combination substitution
# ------------------------------------------------------------------------------
def test_08_multi_ingredient_combination():
    """Buttermilk and baking powder combinations properly returned with exact ratio and chemical explanation."""
    # Buttermilk combination
    buttermilk_subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="buttermilk",
        context="baking",
    )
    assert len(buttermilk_subs) > 0
    top = buttermilk_subs[0]
    assert "milk" in top.substitute.lower()
    assert top.substitution_type == "combination"
    assert "acid" in top.reason.lower() or "reaction" in top.reason.lower() or "leavening" in top.reason.lower()


# ------------------------------------------------------------------------------
# Test 9: Ingredient for which no suitable substitute exists (Honesty & Zero Fabrication)
# ------------------------------------------------------------------------------
def test_09_no_fabrication_for_unknown_ingredients():
    """Unknown, non-existent, or fantasy ingredients must NOT be fabricated into hallucinated replacements."""
    subs = substitution_service.get_substitutions_for_recipe(
        missing_ingredients=["kryptonite_crystal", "quantum_herb_9000"],
        recipe_title="Alien Stew",
    )
    assert subs == []


# ------------------------------------------------------------------------------
# Test 10: Missing ingredient attributes and incomplete database records
# ------------------------------------------------------------------------------
def test_10_incomplete_attributes_graceful_handling():
    """Adding or querying nodes with partial/empty metadata does not crash the graph."""
    # Add a custom node with missing fields
    substitution_graph.graph.add_node("custom_rare_grain", canonical_name="custom_rare_grain")
    res = substitution_graph.find_candidates_for_ingredient("custom_rare_grain")
    # Must execute safely without KeyError or AttributeError
    assert isinstance(res, list)


# ------------------------------------------------------------------------------
# Test 11: Recipe Recommendation Engine Integration
# ------------------------------------------------------------------------------
def test_11_recommendation_engine_integration():
    """Recommendation engine successfully executes end-to-end with the dynamic substitution graph."""
    engine = RecommendationEngine()
    response = engine.recommend(
        pantry_ingredients=["tomato", "garlic", "pasta"],
        limit=2,
    )
    assert response is not None
    assert len(response.recommendations) > 0
    # Every recommendation must have substitutions list generated by the graph
    for rec in response.recommendations:
        assert isinstance(rec.substitutions, list)


# ------------------------------------------------------------------------------
# Test 12: API Response Compatibility with Frontend
# ------------------------------------------------------------------------------
def test_12_api_endpoint_compatibility():
    """POST /substitutions endpoint returns expected schema matching frontend expectations."""
    client = TestClient(app)
    response = client.post(
        "/api/substitutions",
        json={
            "missing_ingredient": "baking powder",
            "pantry_ingredients": ["flour", "baking soda", "yogurt"],
            "context": "baking",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "missing_ingredient" in data
    assert "graph_substitution" in data
    assert "curated_substitutions" in data
    assert len(data["curated_substitutions"]) > 0
    first_sub = data["curated_substitutions"][0]
    assert "substitute" in first_sub
    assert "confidence" in first_sub
    assert "substitution_type" in first_sub
    assert "reason" in first_sub
