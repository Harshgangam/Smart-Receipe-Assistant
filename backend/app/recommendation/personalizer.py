from typing import Any, Dict, List, Optional, Tuple

from backend.app.config import settings


def is_dietary_compatible(
    recipe_dietary: Optional[str],
    user_preference: Optional[str],
) -> bool:
    """
    Check if a recipe satisfies the user's hard dietary restriction.
    - 'vegetarian': Excludes 'non_vegetarian' recipes.
    - 'vegan': Excludes 'non_vegetarian' and 'vegetarian_compatible' (dairy/egg) recipes.
    - 'non_vegetarian': Excludes non-meat recipes when explicitly filtered for non-vegetarian meals.
    - Unknown/None recipe dietary compatibility is retained unless strictly filtered.
    """
    if not user_preference:
        return True

    user_pref = user_preference.lower()
    recipe_diet = (recipe_dietary or "").lower()

    if user_pref in ("vegetarian", "vegetarian_compatible", "veg"):
        if recipe_diet in ("non_vegetarian", "non-vegetarian", "non_veg"):
            return False
        return True

    if user_pref in ("vegan", "vegan_compatible"):
        if recipe_diet in ("non_vegetarian", "non-vegetarian", "non_veg", "vegetarian_compatible"):
            return False
        return True

    if user_pref in ("non_vegetarian", "non-vegetarian", "non_veg"):
        if recipe_diet in ("non_vegetarian", "non-vegetarian", "non_veg"):
            return True
        return False

    return True


def calculate_cuisine_bonus(
    recipe_cuisine: Optional[str],
    recipe_confidence: Optional[str],
    user_cuisine: Optional[str],
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate cuisine preference bonus:
    - High confidence match: +15.0
    - Medium confidence match: +10.0
    - Mismatch or unknown: +0.0 (neutral)
    """
    if not user_cuisine:
        return 0.0, {"applied": False, "reason": "no_cuisine_preference"}

    if not recipe_cuisine:
        return 0.0, {
            "applied": False,
            "status": "unknown_recipe_cuisine",
            "message": "Cuisine could not be confidently determined from the available recipe data.",
        }

    if recipe_cuisine.lower() == user_cuisine.lower():
        if recipe_confidence == "high":
            bonus = settings.CUISINE_BONUS_HIGH_CONFIDENCE
        else:
            bonus = settings.CUISINE_BONUS_MEDIUM_CONFIDENCE
        return bonus, {
            "applied": True,
            "status": "matched",
            "matched_cuisine": recipe_cuisine,
            "confidence": recipe_confidence,
            "bonus": bonus,
        }

    return 0.0, {
        "applied": False,
        "status": "mismatched",
        "recipe_cuisine": recipe_cuisine,
        "user_cuisine": user_cuisine,
    }


def calculate_time_adjustment(
    estimated_time_minutes: Optional[int],
    max_time_minutes: Optional[int],
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate cooking time bonus/penalty:
    - Within limit:
        TimeBonus = 10 * ((max_time - estimated_time) / max_time), clamped to [0, 10]
    - Over limit:
        Penalty = min(15.0, 0.2 * (estimated_time - max_time))
    - Unknown time:
        Neutral (+0.0)
    """
    if max_time_minutes is None:
        return 0.0, {"applied": False, "reason": "no_time_preference"}

    if estimated_time_minutes is None:
        return 0.0, {
            "applied": False,
            "status": "unknown_cooking_time",
            "message": "Cooking time could not be reliably extracted from the directions text.",
        }

    if estimated_time_minutes <= max_time_minutes:
        headroom = max_time_minutes - estimated_time_minutes
        bonus = min(settings.TIME_BONUS_MAX, 10.0 * (headroom / max_time_minutes))
        bonus = max(0.0, bonus)
        return round(bonus, 2), {
            "applied": True,
            "status": "within_limit",
            "estimated_time": estimated_time_minutes,
            "max_time": max_time_minutes,
            "bonus": round(bonus, 2),
        }
    else:
        over = estimated_time_minutes - max_time_minutes
        penalty = min(settings.TIME_PENALTY_MAX, settings.TIME_PENALTY_RATE * over)
        return -round(penalty, 2), {
            "applied": True,
            "status": "exceeded_limit",
            "estimated_time": estimated_time_minutes,
            "max_time": max_time_minutes,
            "penalty": round(penalty, 2),
        }


def evaluate_personalization(
    base_score: float,
    recipe_meta: Dict[str, Any],
    user_cuisine: Optional[str] = None,
    user_dietary: Optional[str] = None,
    max_cooking_time: Optional[int] = None,
) -> Tuple[float, Dict[str, Any], str]:
    """
    Evaluates hard dietary restrictions and soft preference bonuses for a candidate recipe.
    """
    recipe_dietary = recipe_meta.get("dietary_compatibility")
    recipe_cuisine = recipe_meta.get("cuisine")
    cuisine_conf = recipe_meta.get("cuisine_confidence")
    estimated_time = recipe_meta.get("estimated_time_minutes")

    # 1. Hard Dietary Restriction Check
    if not is_dietary_compatible(recipe_dietary, user_dietary):
        return -1.0, {"dietary": {"satisfied": False, "preference": user_dietary, "recipe_compatibility": recipe_dietary}}, f"Filtered out: violates {user_dietary} dietary preference."

    matches_dict = {
        "dietary": {
            "preference": user_dietary,
            "recipe_compatibility": recipe_dietary,
            "satisfied": True,
        }
    }

    # 2. Soft Cuisine Preference
    cuisine_bonus, cuisine_info = calculate_cuisine_bonus(
        recipe_cuisine, cuisine_conf, user_cuisine
    )
    matches_dict["cuisine"] = cuisine_info

    # 3. Soft Cooking Time Adjustment
    time_adjustment, time_info = calculate_time_adjustment(
        estimated_time, max_cooking_time
    )
    matches_dict["time"] = time_info

    # 4. Final Personalization Score Calculation
    personalized_score = base_score + cuisine_bonus + time_adjustment
    personalized_score = min(125.0, max(0.0, personalized_score))

    matches_dict["cuisine_bonus"] = cuisine_bonus
    matches_dict["time_adjustment"] = time_adjustment

    # Explanation Generation
    exp_parts = []
    if user_cuisine:
        if cuisine_info.get("status") == "matched":
            exp_parts.append(
                f"matches your {user_cuisine} cuisine preference (+{cuisine_bonus:.1f} pts, {cuisine_conf} confidence)"
            )
        elif cuisine_info.get("status") == "unknown_recipe_cuisine":
            exp_parts.append("cuisine could not be confidently determined from the available recipe data")
        else:
            exp_parts.append(f"recipe is identified as {recipe_cuisine or 'unclassified'} cuisine")

    if user_dietary:
        exp_parts.append(f"satisfies your {user_dietary} dietary preference ({recipe_dietary})")

    if max_cooking_time is not None:
        if time_info.get("status") == "within_limit":
            exp_parts.append(
                f"fits your {max_cooking_time}-minute time limit (estimated {estimated_time} mins, +{time_adjustment:.2f} pts)"
            )
        elif time_info.get("status") in ("exceeded_limit", "over_limit"):
            exp_parts.append(
                f"exceeds your {max_cooking_time}-minute time limit (estimated {estimated_time} mins, {time_adjustment:.2f} penalty)"
            )
        elif time_info.get("status") == "unknown_cooking_time":
            exp_parts.append("cooking time could not be reliably extracted from the directions text")

    if exp_parts:
        explanation = "Personalization: " + "; ".join(exp_parts) + "."
    else:
        explanation = "No specific preferences applied."

    return round(personalized_score, 2), matches_dict, explanation
