from typing import List, Optional
from pydantic import BaseModel, Field


class SubstitutionEntry(BaseModel):
    """
    Knowledge base representation of a single substitution relationship.
    """
    original_ingredient: str
    substitute: str
    ratio: Optional[str] = Field(
        default=None,
        description="Standardized culinary substitution ratio (e.g. '1:1', '1:0.75', '1:0.5'), or None if unquantifiable.",
    )
    confidence: str = Field(
        ...,
        description="Confidence level: 'high' (standard equivalent), 'medium' (functional substitute), or 'low' (emergency fallback).",
    )
    substitution_type: str = Field(
        default="direct",
        description="Category: 'direct' | 'functional' | 'combination' | 'optional_omission'",
    )
    flavor_notes: Optional[str] = Field(
        default=None,
        description="Profile describing flavor impact (e.g. 'earthy umami', 'sweet citrus').",
    )
    texture_notes: Optional[str] = Field(
        default=None,
        description="Texture impact (e.g. 'tender chew', 'melts smoothly').",
    )
    dietary_compatibility: List[str] = Field(
        default_factory=list,
        description="Dietary categories this substitute satisfies: ['vegetarian', 'vegan', 'gluten_free'].",
    )
    allergens: List[str] = Field(
        default_factory=list,
        description="Allergens present in this substitute: ['dairy', 'gluten', 'soy', etc.].",
    )
    use_cases: List[str] = Field(
        default_factory=lambda: ["general"],
        description="Culinary application contexts: e.g. ['baking', 'frying', 'sauces', 'salads', 'general'].",
    )
    reason: str = Field(
        ...,
        description="Culinary justification explaining why the substitute works and expected flavor/texture characteristics.",
    )
    notes: Optional[str] = Field(
        default=None,
        description="Practical culinary guidance or adjustment tips.",
    )
    source: str = Field(
        default="Culinary Reference Standards",
        description="Authoritative reference source for this substitution relationship.",
    )


class SubstitutionCandidate(BaseModel):
    """
    User-facing substitution suggestion presented for a missing recipe ingredient.
    """
    missing_ingredient: str
    substitute: str
    ratio: Optional[str] = None
    confidence: str = Field(..., description="'high' | 'medium' | 'low'")
    substitution_type: str = Field(
        default="direct",
        description="'direct' | 'functional' | 'combination' | 'optional_omission' | 'none'",
    )
    reason: str
    use_case: Optional[str] = None
    dietary_compatible: bool = True
    safety_status: str = Field(
        default="SAFE",
        description="Safety status of the substitute: 'SAFE' | 'CAUTION' | 'BLOCKED'",
    )
    notes: Optional[str] = None
    source: Optional[str] = "Culinary Reference Standards"
    can_omit: bool = Field(
        default=False,
        description="Whether this missing ingredient can be safely omitted without destroying the dish structure.",
    )
    shopping_suggestion: Optional[str] = Field(
        default=None,
        description="Suggested action for adding to shopping list if no pantry substitute is suitable.",
    )
