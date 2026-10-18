"""
backend/app/services/shopping_optimizer.py

Novelty 4: Missing Ingredient Cost & Micro-Shopping Optimizer
Calculates missing item purchase burden, computes Pantry ROI, and generates multi-recipe
micro-shopping plans that group shared missing ingredients across candidate meals.
"""

from typing import Dict, List, Optional, Set
from pydantic import BaseModel

class IngredientPriceInfo(BaseModel):
    ingredient: str
    unit_price: float
    package_size: str
    estimated_package_cost: float
    leftover_risk: str  # "high", "medium", "low"
    shelf_life_days: int

DEFAULT_PRICE_DATABASE: Dict[str, IngredientPriceInfo] = {
    "coconut milk": IngredientPriceInfo(ingredient="coconut milk", unit_price=2.50, package_size="13.5 oz can", estimated_package_cost=2.50, leftover_risk="low", shelf_life_days=365),
    "heavy cream": IngredientPriceInfo(ingredient="heavy cream", unit_price=3.99, package_size="1 pint", estimated_package_cost=3.99, leftover_risk="medium", shelf_life_days=10),
    "paneer": IngredientPriceInfo(ingredient="paneer", unit_price=4.50, package_size="200g block", estimated_package_cost=4.50, leftover_risk="medium", shelf_life_days=14),
    "parmesan cheese": IngredientPriceInfo(ingredient="parmesan cheese", unit_price=4.99, package_size="5 oz wedge", estimated_package_cost=4.99, leftover_risk="low", shelf_life_days=60),
    "fresh basil": IngredientPriceInfo(ingredient="fresh basil", unit_price=2.29, package_size="1 bunch", estimated_package_cost=2.29, leftover_risk="high", shelf_life_days=4),
    "chicken breast": IngredientPriceInfo(ingredient="chicken breast", unit_price=6.99, package_size="1 lb tray", estimated_package_cost=6.99, leftover_risk="medium", shelf_life_days=3),
    "butter": IngredientPriceInfo(ingredient="butter", unit_price=3.49, package_size="4 sticks (1 lb)", estimated_package_cost=3.49, leftover_risk="low", shelf_life_days=90),
    "sour cream": IngredientPriceInfo(ingredient="sour cream", unit_price=2.19, package_size="8 oz tub", estimated_package_cost=2.19, leftover_risk="medium", shelf_life_days=21),
    "pasta": IngredientPriceInfo(ingredient="pasta", unit_price=1.49, package_size="1 lb box", estimated_package_cost=1.49, leftover_risk="low", shelf_life_days=730),
    "olive oil": IngredientPriceInfo(ingredient="olive oil", unit_price=7.99, package_size="16.9 oz bottle", estimated_package_cost=7.99, leftover_risk="low", shelf_life_days=365),
}

class ShoppingItemPlan(BaseModel):
    ingredient: str
    package_size: str
    estimated_cost: float
    used_in_recipes: List[str]
    reuse_count: int
    pantry_roi_score: float
    leftover_risk: str
    recommendation: str

class MicroShoppingPlan(BaseModel):
    selected_recipes: List[str]
    items_to_buy: List[ShoppingItemPlan]
    total_estimated_cost: float
    total_unique_items: int
    pantry_roi_overall: float
    summary: str

class MicroShoppingOptimizer:
    """
    Micro-Shopping Optimizer calculating item costs, Pantry ROI, and multi-recipe shopping bundles.
    """

    def estimate_item_cost(self, ingredient: str) -> IngredientPriceInfo:
        ing_lower = ingredient.lower().strip()
        if ing_lower in DEFAULT_PRICE_DATABASE:
            return DEFAULT_PRICE_DATABASE[ing_lower]

        for key, info in DEFAULT_PRICE_DATABASE.items():
            if key in ing_lower or ing_lower in key:
                return info

        # Default fallback pricing estimate for generic missing item
        return IngredientPriceInfo(
            ingredient=ingredient,
            unit_price=1.99,
            package_size="1 standard package",
            estimated_package_cost=1.99,
            leftover_risk="low",
            shelf_life_days=30,
        )

    def calculate_pantry_roi(
        self,
        cost_info: IngredientPriceInfo,
        reuse_count: int,
    ) -> float:
        """
        Pantry ROI = (Utility / Reuse gained across meals) / (Purchase cost + Leftover risk factor)
        """
        leftover_penalties = {"low": 0.1, "medium": 0.5, "high": 1.2}
        risk_penalty = leftover_penalties.get(cost_info.leftover_risk, 0.5)

        utility = reuse_count * 100.0
        cost_factor = max(1.0, cost_info.estimated_package_cost + risk_penalty * 2.0)

        roi = utility / cost_factor
        return round(roi, 2)

    def generate_shopping_plan(
        self,
        recipe_candidates: List[dict], # [{"title": str, "missing_ingredients": List[str]}]
    ) -> MicroShoppingPlan:
        if not recipe_candidates:
            return MicroShoppingPlan(
                selected_recipes=[],
                items_to_buy=[],
                total_estimated_cost=0.0,
                total_unique_items=0,
                pantry_roi_overall=0.0,
                summary="No recipes selected for shopping plan.",
            )

        # 1. Map missing ingredients to using recipes
        missing_to_recipes: Dict[str, List[str]] = {}
        for r in recipe_candidates:
            title = r.get("title", "Recipe")
            for ing in r.get("missing_ingredients", []):
                norm = ing.lower().strip()
                if norm not in missing_to_recipes:
                    missing_to_recipes[norm] = []
                missing_to_recipes[norm].append(title)

        items_plan: List[ShoppingItemPlan] = []
        total_cost = 0.0
        total_roi = 0.0

        for ing, titles in missing_to_recipes.items():
            cost_info = self.estimate_item_cost(ing)
            reuse_cnt = len(titles)
            roi_score = self.calculate_pantry_roi(cost_info, reuse_cnt)

            rec_str = (
                f"High Pantry ROI! Buying 1 package supports {reuse_cnt} planned meals."
                if reuse_cnt > 1
                else "Single-recipe purchase."
            )

            items_plan.append(
                ShoppingItemPlan(
                    ingredient=cost_info.ingredient,
                    package_size=cost_info.package_size,
                    estimated_cost=cost_info.estimated_package_cost,
                    used_in_recipes=titles,
                    reuse_count=reuse_cnt,
                    pantry_roi_score=roi_score,
                    leftover_risk=cost_info.leftover_risk,
                    recommendation=rec_str,
                )
            )
            total_cost += cost_info.estimated_package_cost
            total_roi += roi_score

        # Sort items by reuse count and ROI
        items_plan.sort(key=lambda x: (x.reuse_count, x.pantry_roi_score), reverse=True)
        avg_roi = round(total_roi / max(1, len(items_plan)), 2)

        recipe_names = [r.get("title", "") for r in recipe_candidates]
        shared_count = sum(1 for item in items_plan if item.reuse_count > 1)

        summary = (
            f"Shopping plan for {len(recipe_candidates)} meals requires {len(items_plan)} items (~${total_cost:.2f}). "
            f"{shared_count} ingredient(s) are shared across multiple meals, maximizing your Pantry ROI."
        )

        return MicroShoppingPlan(
            selected_recipes=recipe_names,
            items_to_buy=items_plan,
            total_estimated_cost=round(total_cost, 2),
            total_unique_items=len(items_plan),
            pantry_roi_overall=avg_roi,
            summary=summary,
        )

shopping_optimizer = MicroShoppingOptimizer()
