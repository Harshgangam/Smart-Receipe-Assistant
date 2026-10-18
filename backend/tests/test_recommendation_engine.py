import sqlite3
import pytest
from fastapi.testclient import TestClient
import pyarrow as pa
import pyarrow.parquet as pq

from backend.app.main import app
from backend.app.models.recommendation import PantryRequest
from backend.app.recommendation.engine import RecommendationEngine
from backend.app.recommendation.normalizer import (
    get_lookup_variants,
    normalize_pantry_ingredient,
    normalize_pantry_list,
    to_plural_form,
    to_singular_form,
)
from backend.app.recommendation.scorer import (
    calculate_final_score,
    calculate_ims,
    calculate_pus,
    generate_explanation,
)


# ---------------------------------------------------------------------------
# Test Fixtures: Synthetic SQLite Index & Parquet Dataset
# ---------------------------------------------------------------------------

@pytest.fixture
def synthetic_engine(tmp_path):
    """
    Creates an isolated RecommendationEngine with a small synthetic dataset:
    - Recipe 1: ["tomato", "onion", "garlic", "pasta", "basil"] (5 items)
    - Recipe 2: ["tomato", "onion", "garlic", "pasta", "cheese"] (5 items)
    - Recipe 3: ["chicken", "rice", "curry powder"] (3 items)
    - Recipe 4: ["tomato", "onion"] (2 items)
    """
    sqlite_path = tmp_path / "test_index.sqlite"
    parquet_path = tmp_path / "test_recipes.parquet"

    # 1. Setup SQLite
    conn = sqlite3.connect(str(sqlite_path))
    with conn:
        conn.execute("""
            CREATE TABLE ingredients (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                recipe_count INTEGER DEFAULT 0
            );
        """)
        conn.execute("""
            CREATE TABLE recipes_metadata (
                recipe_id INTEGER PRIMARY KEY,
                ner_count INTEGER NOT NULL
            );
        """)
        conn.execute("""
            CREATE TABLE recipe_ingredients (
                ingredient_id INTEGER NOT NULL,
                recipe_id INTEGER NOT NULL,
                PRIMARY KEY (ingredient_id, recipe_id)
            );
        """)

        # Ingredients dictionary
        all_ings = [
            (1, "tomato"),
            (2, "onion"),
            (3, "garlic"),
            (4, "pasta"),
            (5, "basil"),
            (6, "cheese"),
            (7, "chicken"),
            (8, "rice"),
            (9, "curry powder"),
        ]
        conn.executemany("INSERT INTO ingredients (id, name) VALUES (?, ?);", all_ings)

        # Metadata
        metadata = [
            (1, 5),  # Recipe 1: 5 ingredients
            (2, 5),  # Recipe 2: 5 ingredients
            (3, 3),  # Recipe 3: 3 ingredients
            (4, 2),  # Recipe 4: 2 ingredients
        ]
        conn.executemany("INSERT INTO recipes_metadata (recipe_id, ner_count) VALUES (?, ?);", metadata)

        # Recipe Ingredients
        links = [
            # Recipe 1: tomato, onion, garlic, pasta, basil
            (1, 1), (2, 1), (3, 1), (4, 1), (5, 1),
            # Recipe 2: tomato, onion, garlic, pasta, cheese
            (1, 2), (2, 2), (3, 2), (4, 2), (6, 2),
            # Recipe 3: chicken, rice, curry powder
            (7, 3), (8, 3), (9, 3),
            # Recipe 4: tomato, onion
            (1, 4), (2, 4),
        ]
        conn.executemany("INSERT INTO recipe_ingredients (ingredient_id, recipe_id) VALUES (?, ?);", links)
    conn.close()

    # 2. Setup Parquet
    schema = pa.schema([
        pa.field("recipe_id", pa.int64()),
        pa.field("title", pa.string()),
        pa.field("ingredients", pa.list_(pa.string())),
        pa.field("directions", pa.list_(pa.string())),
        pa.field("link", pa.string()),
        pa.field("source", pa.string()),
        pa.field("ner", pa.list_(pa.string())),
        pa.field("ner_count", pa.int32()),
    ])

    data = {
        "recipe_id": [1, 2, 3, 4],
        "title": [
            "Pasta Marinara",
            "Cheesy Pasta Bake",
            "Chicken Curry",
            "Tomato Onion Quick Salad",
        ],
        "ingredients": [
            ["1 can tomatoes", "1 onion", "2 cloves garlic", "1 lb pasta", "fresh basil"],
            ["1 can tomatoes", "1 onion", "2 cloves garlic", "1 lb pasta", "1 cup cheese"],
            ["1 lb chicken", "2 cups rice", "1 tbsp curry powder"],
            ["2 tomatoes", "1 onion"],
        ],
        "directions": [
            ["Cook sauce and pasta", "Serve hot."],
            ["Bake pasta with cheese", "Brown top."],
            ["Cook chicken with curry", "Serve over rice."],
            ["Chop tomatoes and onions finely into bite-sized cubes.", "Toss together in a salad bowl and dress with vinegar and oil."],
        ],
        "link": ["http://ex.com/1", "http://ex.com/2", "http://ex.com/3", "http://ex.com/4"],
        "source": ["Gathered", "Gathered", "Recipes1M", "Gathered"],
        "ner": [
            ["tomato", "onion", "garlic", "pasta", "basil"],
            ["tomato", "onion", "garlic", "pasta", "cheese"],
            ["chicken", "rice", "curry powder"],
            ["tomato", "onion"],
        ],
        "ner_count": [5, 5, 3, 2],
    }

    table = pa.Table.from_pydict(data, schema=schema)
    pq.write_table(table, str(parquet_path))

    return RecommendationEngine(
        sqlite_path=sqlite_path,
        parquet_path=parquet_path,
        ims_weight=0.6,
        pus_weight=0.4,
        candidate_limit=50,
    )


# ---------------------------------------------------------------------------
# Tests A to K
# ---------------------------------------------------------------------------

def test_scenario_a_exact_match(synthetic_engine):
    """A. Exact match: Pantry contains all recipe ingredients -> IMS = 100.0"""
    pantry = ["tomato", "onion"]
    res = synthetic_engine.recommend(pantry, limit=10)

    recipe_4 = next(r for r in res.recommendations if r.recipe_id == 4)
    assert recipe_4.ims == 100.0
    assert len(recipe_4.missing_ingredients) == 0
    assert set(recipe_4.matched_ingredients) == {"tomato", "onion"}


def test_scenario_b_partial_match(synthetic_engine):
    """
    B. Partial match: Recipe 1 requires 5 ingredients.
    Pantry has 4 of them -> IMS = 80.0
    """
    pantry = ["tomato", "onion", "garlic", "pasta", "cheese"]
    res = synthetic_engine.recommend(pantry, limit=10)

    recipe_1 = next(r for r in res.recommendations if r.recipe_id == 1)
    assert recipe_1.ims == 80.0
    assert recipe_1.missing_ingredients == ["basil"]
    assert set(recipe_1.matched_ingredients) == {"tomato", "onion", "garlic", "pasta"}


def test_scenario_c_no_match(synthetic_engine):
    """C. No match: Recipes sharing 0 pantry ingredients must not be returned."""
    # Pantry only has ingredients matching Recipe 3
    pantry = ["chicken", "rice"]
    res = synthetic_engine.recommend(pantry, limit=10)

    recommended_ids = [r.recipe_id for r in res.recommendations]
    assert 3 in recommended_ids
    # Recipes 1, 2, 4 share 0 ingredients with [chicken, rice]
    assert 1 not in recommended_ids
    assert 2 not in recommended_ids
    assert 4 not in recommended_ids


def test_scenario_d_pantry_utilization(synthetic_engine):
    """
    D. Pantry Utilization Score: Verify PUS behaves independently from IMS.
    Pantry: tomato, onion, garlic, pasta, cheese, basil (6 relevant items)
    Recipe 2 uses 5 of 6 -> PUS = 5/6 * 100 = 83.33% (and IMS = 5/5 * 100 = 100%)
    Recipe 4 uses 2 of 6 -> PUS = 2/6 * 100 = 33.33% (and IMS = 2/2 * 100 = 100%)
    """
    pantry = ["tomato", "onion", "garlic", "pasta", "cheese", "basil"]
    res = synthetic_engine.recommend(pantry, limit=10)

    rec_2 = next(r for r in res.recommendations if r.recipe_id == 2)
    rec_4 = next(r for r in res.recommendations if r.recipe_id == 4)

    # Both recipes have 100% IMS (pantry has all their ingredients)
    assert rec_2.ims == 100.0
    assert rec_4.ims == 100.0

    # But their PUS differs based on how much of the pantry they consume!
    assert rec_2.pus == round((5 / 6) * 100.0, 2)  # 83.33
    assert rec_4.pus == round((2 / 6) * 100.0, 2)  # 33.33

    # Recipe 2 has a higher recommendation score because it utilizes more pantry items
    assert rec_2.recommendation_score > rec_4.recommendation_score


def test_scenario_e_multiple_candidate_ranking(synthetic_engine):
    """E. Multiple candidate recipes: Verify ranking order."""
    pantry = ["tomato", "onion", "garlic", "pasta", "cheese"]
    res = synthetic_engine.recommend(pantry, limit=10)

    scores = [r.recommendation_score for r in res.recommendations]
    assert scores == sorted(scores, reverse=True)

    # Recipe 2 matches 5/5 ingredients (IMS=100, PUS=100 -> Score=100.0) -> must be #1
    top_recipe = res.recommendations[0]
    assert top_recipe.recipe_id == 2
    assert top_recipe.recommendation_score == 100.0


def test_scenario_f_missing_ingredients(synthetic_engine):
    """F. Missing ingredients: Verify correct set difference."""
    pantry = ["pasta", "garlic"]
    # Recipe 1 needs: tomato, onion, garlic, pasta, basil
    res = synthetic_engine.recommend(pantry, limit=10)
    rec_1 = next(r for r in res.recommendations if r.recipe_id == 1)

    assert set(rec_1.matched_ingredients) == {"pasta", "garlic"}
    assert set(rec_1.missing_ingredients) == {"tomato", "onion", "basil"}


def test_scenario_g_duplicate_pantry_ingredients(synthetic_engine):
    """G. Duplicate pantry ingredients: Ensure duplicates do not inflate scores."""
    pantry_with_dupes = ["tomato", "TOMATO", "tomato ", "onion", "onion"]
    pantry_clean = ["tomato", "onion"]

    res_dupes = synthetic_engine.recommend(pantry_with_dupes, limit=10)
    res_clean = synthetic_engine.recommend(pantry_clean, limit=10)

    assert res_dupes.normalized_pantry == res_clean.normalized_pantry
    assert len(res_dupes.recommendations) == len(res_clean.recommendations)
    for r1, r2 in zip(res_dupes.recommendations, res_clean.recommendations):
        assert r1.recipe_id == r2.recipe_id
        assert r1.ims == r2.ims
        assert r1.pus == r2.pus
        assert r1.recommendation_score == r2.recommendation_score


def test_scenario_h_empty_pantry(synthetic_engine):
    """H. Empty pantry: Return clean validation response rather than crashing."""
    # Direct engine call with empty list
    res = synthetic_engine.recommend([], limit=10)
    assert res.recommendations == []
    assert res.normalized_pantry == []

    # Via Pydantic model validation
    with pytest.raises(ValueError):
        PantryRequest(pantry_ingredients=[])

    with pytest.raises(ValueError):
        PantryRequest(pantry_ingredients=["  ", ""])


def test_scenario_i_unknown_pantry_ingredient(synthetic_engine):
    """I. Unknown pantry ingredient: Handle gracefully."""
    pantry = ["unknown_space_fruit_999", "tomato"]
    res = synthetic_engine.recommend(pantry, limit=10)

    # Should not crash, and should still recommend tomato recipes
    assert len(res.recommendations) > 0
    recipe_ids = [r.recipe_id for r in res.recommendations]
    assert 4 in recipe_ids


def test_scenario_j_deterministic_ranking(synthetic_engine):
    """J. Deterministic ranking: Repeated identical requests produce identical ordering."""
    pantry = ["tomato", "onion", "garlic", "pasta"]

    res1 = synthetic_engine.recommend(pantry, limit=10)
    res2 = synthetic_engine.recommend(pantry, limit=10)

    assert [r.recipe_id for r in res1.recommendations] == [r.recipe_id for r in res2.recommendations]
    assert [r.recommendation_score for r in res1.recommendations] == [r.recommendation_score for r in res2.recommendations]


def test_scenario_k_api_integration():
    """K. API integration test: Test POST /api/recommendations via TestClient."""
    client = TestClient(app)

    payload = {
        "pantry_ingredients": ["tomato", "onion", "garlic"],
        "limit": 5,
    }
    response = client.post("/api/recommendations", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "normalized_pantry" in data
    assert "relevant_pantry" in data
    assert "recommendations" in data
    assert isinstance(data["recommendations"], list)

    if data["recommendations"]:
        first = data["recommendations"][0]
        assert "recipe_id" in first
        assert "title" in first
        assert "ims" in first
        assert "pus" in first
        assert "recommendation_score" in first
        assert "explanation" in first
        assert "explanation_data" in first
        # Verify explanation text contains expected template structure
        assert "This recipe matches" in first["explanation"] or "Recommended because" in first["explanation"]


def test_normalization_rules():
    """Test conservative normalization and plural handling rules."""
    # Lowercase & trimming
    assert normalize_pantry_ingredient("  Fresh Tomatoes  ") == "fresh tomatoes"

    # Plural handling
    assert to_singular_form("tomatoes") == "tomato"
    assert to_singular_form("onions") == "onion"
    assert to_singular_form("cherries") == "cherry"
    assert to_singular_form("eggs") == "egg"

    # Protected singulars ending in 's' must not be stripped
    assert to_singular_form("asparagus") == "asparagus"
    assert to_singular_form("couscous") == "couscous"
    assert to_singular_form("hummus") == "hummus"
    assert to_singular_form("molasses") == "molasses"
    assert to_singular_form("swiss cheese") == "swiss cheese"

    # Multi-word non-collapsing
    assert to_singular_form("chicken breasts") == "chicken breast"  # does not collapse to "chicken"
    assert normalize_pantry_ingredient("garlic powder") == "garlic powder"  # does not collapse to "garlic"
