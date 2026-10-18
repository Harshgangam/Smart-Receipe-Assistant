from typing import List, Optional
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.substitutions.context import detect_culinary_context
from backend.app.substitutions.models import SubstitutionCandidate, SubstitutionEntry
from backend.app.substitutions.service import SubstitutionService, substitution_service


# ==============================================================================
# Unit & Integration Tests for Milestone 4: Substitutions (Scenarios A - M)
# ==============================================================================

def test_scenario_a_no_missing_ingredients():
    """A. Recipe with no missing ingredients: substitutions must be empty."""
    subs = substitution_service.get_substitutions_for_recipe(
        missing_ingredients=[],
        recipe_title="Pasta Marinara",
        directions=["Boil pasta 10 minutes."],
    )
    assert subs == []


def test_scenario_b_one_known_missing_ingredient():
    """B. Recipe with one known missing ingredient: appropriate substitution returned."""
    subs = substitution_service.get_substitutions_for_recipe(
        missing_ingredients=["parmesan cheese"],
        recipe_title="Spaghetti with Parmesan",
        directions=["Grate cheese on top."],
    )
    assert len(subs) >= 1
    sub = subs[0]
    assert sub.missing_ingredient == "parmesan cheese"
    assert sub.substitute in ("pecorino romano", "nutritional yeast")
    assert sub.confidence in ("high", "medium")
    assert sub.reason is not None
    assert len(sub.reason) > 0


def test_scenario_c_multiple_missing_ingredients():
    """C. Recipe with multiple missing ingredients: each handled independently."""
    subs = substitution_service.get_substitutions_for_recipe(
        missing_ingredients=["butter", "garlic"],
        recipe_title="Garlic Butter Shrimp",
        directions=["Saute garlic in skillet with butter."],
    )
    missing_names = {s.missing_ingredient for s in subs}
    assert "butter" in missing_names
    assert "garlic" in missing_names
    assert len(subs) >= 2


def test_scenario_d_unknown_missing_ingredient():
    """D. Unknown missing ingredient: no fabricated substitution (returns empty list)."""
    subs = substitution_service.get_substitutions_for_recipe(
        missing_ingredients=["rare_mystic_root", "dragonfruit_powder"],
        recipe_title="Exotic Dish",
        directions=["Mix well."],
    )
    assert subs == []


def test_scenario_e_high_confidence_substitution():
    """E. High-confidence substitution: correct ratio, reason, confidence."""
    subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="butter",
        context="baking",
    )
    assert len(subs) > 0
    top_sub = subs[0]
    assert top_sub.confidence == "high"
    assert top_sub.ratio in ("1:1", "1:0.75")
    assert "fat" in top_sub.reason.lower() or "moisture" in top_sub.reason.lower()


def test_scenario_f_unknown_ratio():
    """F. Unknown ratio: ratio remains None when unquantified, never fabricated."""
    custom_entry = SubstitutionEntry(
        original_ingredient="mystery_spice",
        substitute="generic_herb",
        ratio=None,
        confidence="medium",
        dietary_compatibility=["vegetarian", "vegan"],
        use_cases=["general"],
        reason="Adds similar herbal earthiness.",
    )
    service = SubstitutionService(database=[custom_entry])
    subs = service.get_substitutions_for_ingredient("mystery_spice")
    assert len(subs) == 1
    assert subs[0].ratio is None


def test_scenario_g_vegan_preference():
    """G. Vegan preference: dairy/animal substitutes rejected, plant-based returned."""
    # For missing 'milk', dairy cream is rejected; soy or almond milk is returned
    subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="milk",
        dietary_preference="vegan",
    )
    assert len(subs) > 0
    for s in subs:
        assert s.dietary_compatible is True
        assert "dairy" not in s.substitute.lower()
        assert s.substitute in ("soy milk", "almond milk", "oat milk")

    # For missing 'butter' under vegan, margarine or olive oil is returned
    butter_subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="butter",
        dietary_preference="vegan",
    )
    assert len(butter_subs) > 0
    for s in butter_subs:
        assert s.substitute in ("margarine", "olive oil", "applesauce")


def test_scenario_h_vegetarian_preference():
    """H. Vegetarian preference: meat/fish broths rejected, vegetable broth returned."""
    subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="chicken broth",
        dietary_preference="vegetarian",
    )
    assert len(subs) > 0
    substitutes = [s.substitute for s in subs]
    assert "vegetable broth" in substitutes
    assert "beef broth" not in substitutes


def test_scenario_i_context_aware_use_case():
    """I. Context-aware use case: baking vs frying context appropriately prioritized."""
    # In Baking: butter -> margarine / applesauce prioritized
    baking_context = detect_culinary_context(
        title="Chocolate Chip Cookies",
        directions=["Preheat oven to 350. Bake on sheet pan for 12 minutes."],
    )
    assert baking_context == "baking"

    baking_subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="butter",
        context=baking_context,
    )
    assert len(baking_subs) > 0
    assert baking_subs[0].substitute in ("margarine", "applesauce")

    # In Frying: butter -> olive oil prioritized
    frying_context = detect_culinary_context(
        title="Sauteed Garlic Mushrooms",
        directions=["Heat skillet over medium heat. Saute in pan for 5 minutes."],
    )
    assert frying_context == "frying"

    frying_subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="butter",
        context=frying_context,
    )
    assert len(frying_subs) > 0
    assert frying_subs[0].substitute == "olive oil"


def test_scenario_j_no_dietary_preference():
    """J. No dietary preference: normal culinary substitutions returned."""
    subs = substitution_service.get_substitutions_for_ingredient("parmesan cheese")
    assert len(subs) > 0
    substitutes = [s.substitute for s in subs]
    assert "pecorino romano" in substitutes


def test_scenario_k_api_integration():
    """K. API integration: POST /api/recommendations returns complete substitution payload."""
    client = TestClient(app)
    # User has pasta, tomato, garlic; recipe may require parmesan or butter
    payload = {
        "pantry_ingredients": ["pasta", "tomato", "garlic"],
        "limit": 5,
    }
    response = client.post("/api/recommendations", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data

    for item in data["recommendations"]:
        assert "missing_ingredients" in item
        assert "missing_count" in item
        assert "substitutions" in item
        assert item["missing_count"] == len(item["missing_ingredients"])
        if item["substitutions"]:
            first_sub = item["substitutions"][0]
            assert "missing_ingredient" in first_sub
            assert "substitute" in first_sub
            assert "confidence" in first_sub
            assert "reason" in first_sub


def test_scenario_m_deterministic_behavior():
    """M. Deterministic behavior: Repeated calls produce identical substitution outcomes."""
    missing = ["butter", "milk", "onion"]
    res1 = substitution_service.get_substitutions_for_recipe(
        missing_ingredients=missing,
        recipe_title="Cream of Onion Soup",
        directions=["Simmer soup in pot."],
        dietary_preference="vegetarian",
    )
    res2 = substitution_service.get_substitutions_for_recipe(
        missing_ingredients=missing,
        recipe_title="Cream of Onion Soup",
        directions=["Simmer soup in pot."],
        dietary_preference="vegetarian",
    )

    assert len(res1) == len(res2)
    for s1, s2 in zip(res1, res2):
        assert s1.missing_ingredient == s2.missing_ingredient
        assert s1.substitute == s2.substitute
        assert s1.ratio == s2.ratio
        assert s1.confidence == s2.confidence
        assert s1.reason == s2.reason


# ==============================================================================
# Additional Tests: Mushrooms, Green Bell Peppers, Pepperoni, Mozzarella & Hard-Locks
# ==============================================================================

def test_mushrooms_substitutions():
    """Verify mushroom candidate evaluation (direct and functional options)."""
    subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="portabello mushrooms",
        context="frying",
    )
    assert len(subs) >= 1
    sub_names = [s.substitute.lower() for s in subs]
    assert any("cremini" in name or "button" in name or "zucchini" in name for name in sub_names)
    assert subs[0].confidence in ("high", "medium")


def test_green_bell_peppers_substitutions():
    """Verify green bell pepper substitutions across color variants and functional crunches."""
    subs = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="green bell pepper",
        context="frying",
    )
    assert len(subs) >= 1
    sub_names = [s.substitute.lower() for s in subs]
    assert any("bell pepper" in name or "poblano" in name or "celery" in name for name in sub_names)


def test_pepperoni_substitutions_and_dietary():
    """Verify pepperoni provides meat equivalents normally and plant alternatives under vegetarian."""
    # General (non-vegetarian)
    subs_gen = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="pepperoni",
        context="baking",
    )
    assert len(subs_gen) >= 1
    assert any("salami" in s.substitute.lower() or "turkey" in s.substitute.lower() for s in subs_gen)

    # Vegetarian Hard-Lock: Pork/beef cured meats must be strictly excluded
    subs_veg = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="pepperoni",
        dietary_preference="vegetarian",
    )
    assert len(subs_veg) >= 1
    for s in subs_veg:
        assert "salami" not in s.substitute.lower()
        assert "chorizo" not in s.substitute.lower()
        assert any(term in s.substitute.lower() for term in ["tofu", "tempeh", "tomato", "olive"])


def test_mozzarella_substitutions_and_allergen_hardlock():
    """Verify mozzarella returns melting cheeses normally and dairy-free options under dairy allergy."""
    # General: Provolone, Monterey Jack, Fontina
    subs_gen = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="mozzarella cheese",
        context="baking",
    )
    assert len(subs_gen) >= 1
    assert any("provolone" in s.substitute.lower() or "jack" in s.substitute.lower() or "fontina" in s.substitute.lower() for s in subs_gen)

    # Allergen Hard-Lock: When user has dairy allergy, dairy cheeses must be blocked
    subs_dairy_free = substitution_service.get_substitutions_for_ingredient(
        missing_ingredient="mozzarella cheese",
        allergens=["dairy"],
    )
    assert len(subs_dairy_free) >= 1
    for s in subs_dairy_free:
        assert "provolone" not in s.substitute.lower()
        assert "cheddar" not in s.substitute.lower()
        assert any(term in s.substitute.lower() for term in ["vegan", "plant-based", "cashew"])


def test_pepperoni_spaghetti_recipe_evaluation():
    """Evaluate Pepperoni Spaghetti fixture (contains mushrooms, green pepper, pepperoni, mozzarella)."""
    fixture_missing = ["green pepper", "sliced pepperoni", "mushrooms", "mozzarella cheese"]
    subs = substitution_service.get_substitutions_for_recipe(
        missing_ingredients=fixture_missing,
        recipe_title="Pepperoni Spaghetti",
        directions=["Combine onion, green pepper, ground beef and pepperoni in a large skillet."],
    )
    missing_covered = {s.missing_ingredient for s in subs}
    # Each missing item evaluated independently and assigned suitable candidates
    assert "green pepper" in missing_covered
    assert "sliced pepperoni" in missing_covered
    assert "mushrooms" in missing_covered
    assert "mozzarella cheese" in missing_covered


def test_universal_missing_ingredient_coverage_and_omission():
    """Test universal coverage: evaluated items with valid substitutes, omissions, and unknown non-fabricated items."""
    test_set = [
        "portabello mushrooms",      # known with direct substitute
        "green bell pepper",         # known with direct substitute
        "parsley",                   # garnish with optional omission
        "extraterrestrial_truffle",  # unknown with no fabrication
    ]
    subs = substitution_service.get_substitutions_for_recipe(
        missing_ingredients=test_set,
        recipe_title="Gourmet Pasta",
        directions=["Cook in skillet."],
    )
    subs_by_item = {s.missing_ingredient: s for s in subs}

    # 1. Known items receive validated substitutes
    assert "portabello mushrooms" in subs_by_item
    assert "green bell pepper" in subs_by_item

    # 2. Garnish receives explicit optional omission option
    assert "parsley" in subs_by_item
    assert subs_by_item["parsley"].substitution_type == "optional_omission"
    assert subs_by_item["parsley"].can_omit is True

    # 3. Unknown item is NOT fabricated
    assert "extraterrestrial_truffle" not in subs_by_item

