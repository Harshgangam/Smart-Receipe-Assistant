from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator

from data_pipeline.enrichment.taxonomy import SUPPORTED_CUISINES
from backend.app.substitutions.models import SubstitutionCandidate


class PantryRequest(BaseModel):
    """
    User request providing available pantry ingredients and optional personalization preferences.
    """
    pantry_ingredients: List[str] = Field(
        ...,
        description="List of ingredients currently available in the user's pantry.",
        min_length=1,
    )
    limit: Optional[int] = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of recommended recipes to return.",
    )
    cuisine: Optional[str] = Field(
        default=None,
        description="Target cuisine preference (e.g. Italian, Indian, Mexican, Chinese).",
    )
    dietary_preference: Optional[str] = Field(
        default=None,
        description="Dietary restriction: 'vegetarian', 'vegan', or 'non_vegetarian'.",
    )
    max_cooking_time_minutes: Optional[int] = Field(
        default=None,
        ge=1,
        description="Maximum acceptable cooking duration in minutes.",
    )
    pantry_items_details: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Optional structured pantry item details including expiry dates and risk levels.",
    )
    allergens: Optional[List[str]] = Field(
        default=None,
        description="List of user allergen ingredients to strictly lock/exclude (e.g. ['gluten', 'shrimp', 'potatoes']).",
    )
    query_text: Optional[str] = Field(
        default=None,
        description="Optional free-text search query or dish name to steer recommendations.",
    )

    @field_validator("pantry_ingredients")
    @classmethod
    def validate_pantry_not_empty(cls, v: List[str]) -> List[str]:
        cleaned = [item.strip() for item in v if item and item.strip()]
        if not cleaned:
            raise ValueError("Pantry ingredients list must contain at least one non-empty ingredient.")
        return cleaned

    @field_validator("cuisine")
    @classmethod
    def validate_cuisine(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_clean = v.strip().title()
        valid_map = {c.lower(): c for c in SUPPORTED_CUISINES}
        if v_clean.lower() not in valid_map:
            raise ValueError(
                f"Unsupported cuisine '{v}'. Supported cuisines: {', '.join(SUPPORTED_CUISINES)}"
            )
        return valid_map[v_clean.lower()]

    @field_validator("dietary_preference")
    @classmethod
    def validate_dietary_preference(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v_clean = v.strip().lower()
        if v_clean in ("vegetarian", "vegetarian_compatible"):
            return "vegetarian"
        if v_clean in ("vegan", "vegan_compatible"):
            return "vegan"
        if v_clean in ("non_vegetarian", "non-vegetarian", "non_veg"):
            return "non_vegetarian"
        raise ValueError(
            f"Unsupported dietary preference '{v}'. Supported options: 'vegetarian', 'vegan', 'non_vegetarian'"
        )

    @field_validator("max_cooking_time_minutes")
    @classmethod
    def validate_cooking_time(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v <= 0:
            raise ValueError("max_cooking_time_minutes must be a positive integer.")
        return v


class PantryCookRequest(BaseModel):
    recipe_id: int
    recipe_title: str
    recipe_ner: List[str]


class PantryScanResponse(BaseModel):
    detected_items: List[Dict[str, Any]]
    added_to_pantry_count: int
    scan_summary: str


class ExplanationData(BaseModel):
    """Structured decision explanation data for Explainable AI (XAI)."""
    matched_ingredients: List[str]
    missing_ingredients: List[str]
    matched_count: int
    total_recipe_ingredients: int
    relevant_pantry_used_count: int
    relevant_pantry_total_count: int
    ims: float
    pus: float
    base_score: Optional[float] = None
    final_score: float

    why_this_recipe: Optional[str] = None
    cuisine_bonus: float = 0.0
    time_adjustment: float = 0.0
    dietary_filter_applied: Optional[str] = None


class RecipeRecommendationItem(BaseModel):
    """Single ranked recipe recommendation item with grounded explanations and metadata."""
    recipe_id: int
    title: str
    ingredients: List[str]
    directions: List[str]
    link: Optional[str] = None
    source: Optional[str] = None
    ner: List[str]
    matched_ingredients: List[str]
    missing_ingredients: List[str]
    missing_count: int
    missing_categorized: Optional[Dict[str, List[str]]] = None
    can_prepare_without_missing: bool = True
    substitutions: List[SubstitutionCandidate] = Field(default_factory=list)
    ims: float
    pus: float
    recommendation_score: float

    image_url: Optional[str] = None
    safety_status: Optional[str] = "SAFE"
    safety_reasons: List[str] = Field(default_factory=list)
    estimated_missing_cost: float = 0.0
    food_waste_score: float = 0.0

    why_this_recipe: Optional[str] = None
    explanation: str
    explanation_data: ExplanationData
    cuisine: Optional[str] = None
    cuisine_confidence: Optional[str] = None
    dietary_compatibility: Optional[str] = None
    dietary_confidence: Optional[str] = None
    estimated_time_minutes: Optional[int] = None
    time_confidence: Optional[str] = None
    preference_matches: Dict[str, Any] = Field(default_factory=dict)
    preference_explanation: Optional[str] = None


class RecommendationResponse(BaseModel):
    """Root response structure returned by the recommendation engine API."""
    normalized_pantry: List[str]
    relevant_pantry: List[str]
    total_candidates_evaluated: int
    applied_preferences: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[RecipeRecommendationItem]
