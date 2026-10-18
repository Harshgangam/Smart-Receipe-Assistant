import pytest
from fastapi.testclient import TestClient

from backend.app.assistant.context_assembler import context_assembler
from backend.app.assistant.llm_client import MockLLMClient
from backend.app.assistant.models import AssistantRequest, AssistantTask
from backend.app.assistant.service import assistant_service
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


# Sample real recipe ID present in dataset: Bowtie Pasta & Mushrooms (1316605)
SAMPLE_RECIPE_ID = 1316605


def test_context_assembler_valid_recipe():
    """Verify ContextAssembler extracts authoritative structured context from Parquet and SQLite."""
    pantry = ["pasta", "garlic", "olive oil"]
    context = context_assembler.assemble_context(
        recipe_id=SAMPLE_RECIPE_ID,
        pantry_ingredients=pantry,
        cuisine="Italian",
        dietary_preference="vegetarian",
        max_cooking_time_minutes=30,
    )

    assert context is not None
    assert context.recipe_id == SAMPLE_RECIPE_ID
    assert "Bowtie" in context.title or "Pasta" in context.title
    assert len(context.ingredients) > 0
    assert len(context.directions) > 0
    assert len(context.ner) > 0
    assert "garlic" in context.matched_ingredients or "pasta" in context.matched_ingredients
    assert context.ims > 0.0
    assert context.pus > 0.0
    assert context.recommendation_score > 0.0
    assert context.cuisine == "Italian"


def test_context_assembler_nonexistent_recipe():
    """Verify ContextAssembler returns None for a non-existent recipe ID."""
    context = context_assembler.assemble_context(recipe_id=999999999)
    assert context is None


def test_mock_llm_client_explain():
    """Verify MockLLMClient produces an explain response grounded in IMS, PUS, and matched ingredients."""
    context = context_assembler.assemble_context(
        recipe_id=SAMPLE_RECIPE_ID,
        pantry_ingredients=["pasta", "garlic", "olive oil"],
        cuisine="Italian",
    )
    assert context is not None

    client = MockLLMClient()
    answer = client.generate("", "", context, AssistantTask.EXPLAIN)

    assert context.title in answer
    assert "Ingredient Match Score" in answer
    assert f"{context.ims:.1f}%" in answer
    assert "Pantry Utilization Score" in answer


def test_mock_llm_client_simplify():
    """Verify MockLLMClient formats directions into clear numbered steps."""
    context = context_assembler.assemble_context(
        recipe_id=SAMPLE_RECIPE_ID,
        pantry_ingredients=["pasta", "garlic", "olive oil"],
    )
    assert context is not None

    client = MockLLMClient()
    answer = client.generate("", "", context, AssistantTask.SIMPLIFY)

    assert "1." in answer
    assert "simplified" in answer.lower()
    assert context.title in answer


def test_mock_llm_client_guidance():
    """Verify MockLLMClient outlines pantry prep steps and incorporates substitutions."""
    context = context_assembler.assemble_context(
        recipe_id=SAMPLE_RECIPE_ID,
        pantry_ingredients=["pasta", "garlic", "olive oil"],
    )
    assert context is not None

    client = MockLLMClient()
    answer = client.generate("", "", context, AssistantTask.GUIDANCE)

    assert "Pantry-Aware" in answer or "pantry" in answer.lower()
    assert "Prep on-hand pantry ingredients" in answer


def test_mock_llm_client_question_verified_substitution():
    """Verify MockLLMClient correctly cites verified substitution when queried."""
    context = context_assembler.assemble_context(
        recipe_id=SAMPLE_RECIPE_ID,
        pantry_ingredients=["pasta", "garlic", "olive oil"],
    )
    assert context is not None

    client = MockLLMClient()
    # Recipe 1316605 has missing 'fresh basil' or 'basil' which maps to 'dried basil'
    answer = client.generate(
        "",
        "",
        context,
        AssistantTask.QUESTION,
        question="Can I substitute fresh basil in this recipe?",
    )

    assert "dried basil" in answer.lower() or "basil" in answer.lower()
    assert "knowledge base" in answer.lower() or "curated" in answer.lower()


def test_mock_llm_client_question_unsupported_substitution():
    """Verify MockLLMClient explicitly refuses to fabricate substitutes for unverified items."""
    context = context_assembler.assemble_context(
        recipe_id=SAMPLE_RECIPE_ID,
        pantry_ingredients=["pasta", "garlic", "olive oil"],
    )
    assert context is not None

    client = MockLLMClient()
    # Mushrooms has no verified substitute in our curated knowledge base
    answer = client.generate(
        "",
        "",
        context,
        AssistantTask.QUESTION,
        question="Can I substitute apples for the mushrooms in this dish?",
    )

    assert "cannot confirm a reliable culinary substitute" in answer.lower()


def test_assistant_service_citations():
    """Verify AssistantService extracts grounding citations and records used substitutions."""
    req = AssistantRequest(
        recipe_id=SAMPLE_RECIPE_ID,
        task=AssistantTask.EXPLAIN,
        pantry_ingredients=["pasta", "garlic", "olive oil"],
        cuisine="Italian",
    )
    resp = assistant_service.get_guidance(req)

    assert resp.recipe_id == SAMPLE_RECIPE_ID
    assert isinstance(resp.is_mock, bool)
    assert len(resp.citations) > 0
    citation_types = [c.source_type for c in resp.citations]
    assert "pantry_match" in citation_types or "derived_metadata" in citation_types


def test_api_assistant_ask_endpoint(client):
    """Verify POST /api/assistant/ask successfully returns structured response."""
    payload = {
        "recipe_id": SAMPLE_RECIPE_ID,
        "task": "explain",
        "pantry_ingredients": ["pasta", "garlic", "olive oil"],
        "cuisine": "Italian",
    }
    response = client.post("/api/assistant/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["recipe_id"] == SAMPLE_RECIPE_ID
    assert data["task"] == "explain"
    assert len(data["answer"]) > 0
    assert "citations" in data
    assert isinstance(data["is_mock"], bool)


def test_api_assistant_status_endpoint(client):
    """Verify GET /api/assistant/status returns assistant configuration."""
    response = client.get("/api/assistant/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "online"
    assert "provider" in data
    assert "model" in data
    assert isinstance(data["is_mock"], bool)


def test_api_assistant_ask_404_not_found(client):
    """Verify POST /api/assistant/ask returns 404 for invalid recipe ID."""
    payload = {
        "recipe_id": 999999999,
        "task": "explain",
        "pantry_ingredients": ["tomato"],
    }
    response = client.post("/api/assistant/ask", json=payload)
    assert response.status_code == 404


# ==============================================================================
# Milestone 6 Custom Q&A Grounding Tests (Scenarios A through F)
# ==============================================================================

def test_custom_qa_cooking_step_grounded_in_directions():
    """Scenario A: Custom question about cooking steps returns directions-grounded sequence."""
    # Recipe 1670510: 'Bow tie pasta a la you'
    context = context_assembler.assemble_context(
        recipe_id=1670510,
        pantry_ingredients=["pasta", "olive oil", "garlic", "onion", "tomatoes"],
    )
    assert context is not None

    client = MockLLMClient()
    answer = client.generate(
        "",
        "",
        context,
        AssistantTask.QUESTION,
        question="How should I cook the sausage before adding the pasta?",
    )

    # Must contain specific direction steps and mention sausage / links / skillet
    assert "sausage" in answer.lower() or "links" in answer.lower()
    assert "Step 1" in answer
    assert "Step 3" in answer or "Step 7" in answer
    assert "skillet" in answer.lower() or "cook" in answer.lower()
    assert "pasta" in answer.lower()


def test_custom_qa_ingredient_usage_grounded():
    """Scenario B: Custom question about ingredient usage returns grounded steps."""
    context = context_assembler.assemble_context(
        recipe_id=1670510,
        pantry_ingredients=["pasta", "olive oil", "garlic", "onion", "tomatoes"],
    )
    assert context is not None

    client = MockLLMClient()
    answer = client.generate(
        "",
        "",
        context,
        AssistantTask.QUESTION,
        question="How is garlic used in this recipe?",
    )

    assert "garlic" in answer.lower()
    assert "Step 4" in answer or "Step 5" in answer
    assert "skillet" in answer.lower() or "drippings" in answer.lower() or "flavor" in answer.lower()


def test_custom_qa_cooking_time():
    """Scenario C: Custom question about cooking time returns known time."""
    context = context_assembler.assemble_context(
        recipe_id=SAMPLE_RECIPE_ID,
        pantry_ingredients=["pasta", "garlic", "olive oil"],
    )
    assert context is not None

    client = MockLLMClient()
    answer = client.generate(
        "",
        "",
        context,
        AssistantTask.QUESTION,
        question="How long does this recipe take to cook?",
    )

    assert "estimated active cooking time" in answer.lower()
    assert str(context.estimated_time_minutes) in answer


def test_custom_qa_pantry_availability():
    """Scenario D: Custom question about pantry availability returns pantry context."""
    context = context_assembler.assemble_context(
        recipe_id=1670510,
        pantry_ingredients=["pasta", "olive oil", "garlic", "onion", "tomatoes"],
    )
    assert context is not None

    client = MockLLMClient()

    # Query available item
    ans_available = client.generate(
        "",
        "",
        context,
        AssistantTask.QUESTION,
        question="Do I have tomatoes in my pantry?",
    )
    assert "available in your pantry" in ans_available.lower() or "tomatoes" in ans_available.lower()

    # Query missing items
    ans_missing = client.generate(
        "",
        "",
        context,
        AssistantTask.QUESTION,
        question="What ingredients am I missing?",
    )
    assert "missing" in ans_missing.lower()
    assert "zucchini" in ans_missing.lower() or "salt" in ans_missing.lower()


def test_custom_qa_unknown_unanswerable_no_hallucination():
    """Scenario F: Unanswerable or absent question safely declines without hallucination."""
    context = context_assembler.assemble_context(
        recipe_id=1670510,
        pantry_ingredients=["pasta", "olive oil", "garlic", "onion", "tomatoes"],
    )
    assert context is not None

    client = MockLLMClient()
    answer = client.generate(
        "",
        "",
        context,
        AssistantTask.QUESTION,
        question="What temperature should the oven be set to for baking?",
    )

    # Must refuse or state information is not provided, rather than inventing an oven temperature
    assert "do not contain information" in answer.lower() or "do not specify" in answer.lower() or "couldn't find" in answer.lower()
    assert "400" not in answer and "350" not in answer and "degrees" not in answer

