from backend.app.recommendation.normalizer import (
    get_lookup_variants,
    normalize_pantry_ingredient,
    normalize_pantry_list,
    to_singular_form,
)
from backend.app.recommendation.scorer import (
    calculate_final_score,
    calculate_ims,
    calculate_pus,
    generate_explanation,
)

def __getattr__(name: str):
    if name == "RecommendationEngine":
        from backend.app.recommendation.engine import RecommendationEngine
        return RecommendationEngine
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

__all__ = [
    "RecommendationEngine",
    "normalize_pantry_ingredient",
    "normalize_pantry_list",
    "to_singular_form",
    "get_lookup_variants",
    "calculate_ims",
    "calculate_pus",
    "calculate_final_score",
    "generate_explanation",
]
