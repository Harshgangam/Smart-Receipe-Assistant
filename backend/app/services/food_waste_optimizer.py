"""
backend/app/services/food_waste_optimizer.py

Novelty 3: Food Waste Minimization Engine
Multi-objective optimization balancing Pantry Usage (PUS), Near-Expiry Item Urgency (ExpiryPriority),
and Missing Purchase Cost.
"""

from datetime import datetime, date
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel

class ExpiryItemInfo(BaseModel):
    ingredient: str
    expiry_date: Optional[str] = None  # YYYY-MM-DD
    days_to_expiry: Optional[int] = None
    urgency_weight: float = 0.1

class OptimizationWeights(BaseModel):
    pantry_usage: float = 0.4
    expiry_priority: float = 0.3
    shopping_cost: float = 0.3

class WasteOptimizationResult(BaseModel):
    recipe_id: int
    recipe_title: str
    pantry_usage_score: float
    expiry_priority_score: float
    missing_items_count: int
    estimated_missing_cost: float
    composite_waste_score: float
    rescuing_expiring_items: List[str]
    rationale: str

class FoodWasteOptimizer:
    """
    Multi-objective recommendation optimizer steering recipe selection toward food-waste reduction.
    """

    def calculate_expiry_urgency(self, expiry_date_str: Optional[str]) -> Tuple[int, float]:
        """
        Converts expiry date string into days remaining and normalized urgency weight.
        """
        if not expiry_date_str:
            return 999, 0.1

        try:
            exp_date = datetime.strptime(expiry_date_str, "%Y-%m-%d").date()
            today = date.today()
            delta_days = (exp_date - today).days

            if delta_days <= 1:
                return delta_days, 1.0
            elif delta_days <= 3:
                return delta_days, 0.85
            elif delta_days <= 7:
                return delta_days, 0.6
            elif delta_days <= 14:
                return delta_days, 0.3
            else:
                return delta_days, 0.1
        except Exception:
            return 999, 0.1

    def optimize_recipe_ranking(
        self,
        recipe_id: int,
        title: str,
        matched_ingredients: List[str],
        missing_ingredients: List[str],
        pantry_expiry_map: Dict[str, str],  # ingredient_name -> YYYY-MM-DD
        total_pantry_count: int,
        estimated_missing_cost: float = 0.0,
        weights: Optional[OptimizationWeights] = None,
    ) -> WasteOptimizationResult:
        weights = weights or OptimizationWeights()

        # 1. Pantry Usage Score (0 - 100)
        used_pantry_count = len(matched_ingredients)
        pus = (used_pantry_count / total_pantry_count * 100.0) if total_pantry_count > 0 else 0.0

        # 2. Expiry Priority Score (0 - 100)
        rescuing_items = []
        total_urgency = 0.0

        for ing in matched_ingredients:
            ing_lower = ing.lower().strip()
            exp_date = pantry_expiry_map.get(ing_lower)
            if not exp_date:
                # Substring check
                for p_ing, p_exp in pantry_expiry_map.items():
                    if p_ing in ing_lower or ing_lower in p_ing:
                        exp_date = p_exp
                        break

            days, urgency = self.calculate_expiry_urgency(exp_date)
            total_urgency += urgency
            if days <= 7 and exp_date:
                rescuing_items.append(f"{ing} (expires in {days}d)")

        expiry_score = min(100.0, (total_urgency / max(1, used_pantry_count)) * 100.0) if used_pantry_count > 0 else 0.0

        # 3. Missing Purchase Burden Penalty
        missing_count = len(missing_ingredients)
        cost_penalty = min(50.0, estimated_missing_cost * 2.0 + missing_count * 5.0)

        # 4. Multi-Objective Composite Score
        composite_score = (
            weights.pantry_usage * pus +
            weights.expiry_priority * expiry_score -
            weights.shopping_cost * cost_penalty
        )
        composite_score = min(100.0, max(0.0, composite_score))

        # 5. Rationale Generation
        rescue_str = f"Rescues near-expiry items: {', '.join(rescuing_items)}." if rescuing_items else "Uses fresh pantry staples."
        rationale = f"Consumes {used_pantry_count} pantry items ({pus:.1f}% PUS). {rescue_str} Requires {missing_count} missing item(s) (~${estimated_missing_cost:.2f})."

        return WasteOptimizationResult(
            recipe_id=recipe_id,
            recipe_title=title,
            pantry_usage_score=round(pus, 1),
            expiry_priority_score=round(expiry_score, 1),
            missing_items_count=missing_count,
            estimated_missing_cost=round(estimated_missing_cost, 2),
            composite_waste_score=round(composite_score, 1),
            rescuing_expiring_items=rescuing_items,
            rationale=rationale,
        )

food_waste_optimizer = FoodWasteOptimizer()
