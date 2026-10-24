"""
backend/app/substitutions/service.py

Dynamic Smart Substitution Service integrating NetworkX knowledge graph search,
pantry-aware candidate ranking, deterministic allergen and dietary safety hard-locks,
multi-ingredient combinations, and honest handling of unindexed ingredients.
"""

import logging
import re
from typing import Dict, List, Optional, Set, Tuple

from backend.app.safety.allergen_guard import ALLERGEN_TAXONOMY
from backend.app.substitutions.context import detect_culinary_context
from backend.app.substitutions.graph import substitution_graph
from backend.app.substitutions.knowledge_base import SUBSTITUTION_DATABASE
from backend.app.substitutions.models import SubstitutionCandidate, SubstitutionEntry
from backend.app.substitutions.normalizer import resolve_canonical_ingredient

logger = logging.getLogger(__name__)

# Essential structural ingredients that should NOT be omitted without changing the recipe outcome
STRUCTURAL_PIVOTAL_INGREDIENTS: Set[str] = {
    "flour", "all-purpose flour", "egg", "eggs", "baking powder", "baking soda",
    "yeast", "sugar", "ground beef", "chicken", "spaghetti", "pasta"
}

# Optional garnish or flavor booster ingredients that can be safely omitted
OPTIONAL_GARNISH_INGREDIENTS: Set[str] = {
    "parsley", "cilantro", "fresh basil", "basil", "oregano", "black pepper",
    "red pepper flakes", "paprika", "sesame seeds", "green onion", "chives"
}


class SubstitutionService:
    """
    Intelligent substitution engine combining:
      1. NetworkX Dynamic Smart Substitution Graph (SQLite-backed).
      2. Multi-ingredient functional combinations (e.g., baking powder -> baking soda + yogurt/acid).
      3. Role-based & attribute graph traversal for unindexed ingredients.
      4. Deterministic Allergen & Dietary Safety Hard-Locks.
      5. Pantry-aware scoring and prioritization.
      6. Honest reporting when no reliable substitute exists (zero fabrication).
    """

    def __init__(self, database: Optional[List[SubstitutionEntry]] = None):
        self.database = database or SUBSTITUTION_DATABASE
        self.graph = substitution_graph
        self._index: Dict[str, List[SubstitutionEntry]] = {}
        for entry in self.database:
            key = entry.original_ingredient.lower().strip()
            if key not in self._index:
                self._index[key] = []
            self._index[key].append(entry)

    def lookup_raw_entries(self, ingredient_name: str) -> List[SubstitutionEntry]:
        """
        Lookup substitution entries in this service instance's index.
        Applies canonical normalization, alias mapping, and prefix/substring match.
        """
        if not ingredient_name:
            return []

        canonical = resolve_canonical_ingredient(ingredient_name)
        norm = ingredient_name.lower().strip()

        # 1. Exact match by canonical name
        if canonical in self._index:
            return self._index[canonical]

        # 2. Exact match by raw normalized name
        if norm in self._index:
            return self._index[norm]

        # 3. Singular check
        if norm.endswith("s") and norm[:-1] in self._index:
            return self._index[norm[:-1]]
        if canonical.endswith("s") and canonical[:-1] in self._index:
            return self._index[canonical[:-1]]

        # 4. Substring check for compound terms
        for key, entries in self._index.items():
            if key in canonical or canonical in key or key in norm or norm in key:
                return entries

        return []

    def _check_safety(
        self,
        candidate_name: str,
        entry: Optional[SubstitutionEntry] = None,
        dietary_preference: Optional[str] = None,
        allergens: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """
        Deterministic Allergen and Dietary Hard-Lock Filter.
        Guarantees that neither knowledge base entries nor fallbacks bypass safety constraints.
        """
        return self.graph.evaluate_safety(
            candidate_name=candidate_name,
            user_diet=dietary_preference,
            user_allergens=allergens,
        )

    def get_substitutions_for_ingredient(
        self,
        missing_ingredient: str,
        context: str = "general",
        dietary_preference: Optional[str] = None,
        allergens: Optional[List[str]] = None,
        max_candidates: int = 2,
        pantry_items: Optional[List[str]] = None,
    ) -> List[SubstitutionCandidate]:
        """
        Finds appropriate substitution candidates for a single missing ingredient independently.
        Queries the Dynamic Smart Substitution Graph first, evaluating verified edges,
        multi-ingredient combinations, pantry availability, and functional roles.
        """
        if not missing_ingredient or not missing_ingredient.strip():
            return []

        canonical = resolve_canonical_ingredient(missing_ingredient)

        # 1. Check if the missing item is a safe optional garnish
        if canonical in OPTIONAL_GARNISH_INGREDIENTS:
            # Garnish can be omitted without altering core dish structure
            return [
                SubstitutionCandidate(
                    missing_ingredient=missing_ingredient,
                    substitute="Optional omission",
                    ratio=None,
                    confidence="medium",
                    substitution_type="optional_omission",
                    reason=f"{missing_ingredient.capitalize()} serves primarily as a decorative garnish or accent and can be omitted without compromising the core dish structure.",
                    use_case=context,
                    dietary_compatible=True,
                    safety_status="SAFE",
                    can_omit=True,
                    notes="Omit without flavor balance issues.",
                    source="Culinary Institute of America",
                    shopping_suggestion=f"Add {missing_ingredient} to shopping list for full presentation.",
                )
            ]

        # 2. Query the Dynamic Smart Substitution Graph
        graph_candidates = self.graph.find_candidates_for_ingredient(
            missing_ingredient=missing_ingredient,
            pantry_items=pantry_items,
            context=context,
            dietary_preference=dietary_preference,
            user_allergens=allergens,
            max_candidates=max_candidates,
        )

        if graph_candidates:
            return graph_candidates

        # 3. Fallback to raw database index lookup (for custom database instances or unlinked items)
        raw_entries = self.lookup_raw_entries(missing_ingredient)
        if raw_entries:
            compatible_entries: List[SubstitutionEntry] = []
            for entry in raw_entries:
                is_safe, _ = self._check_safety(
                    candidate_name=entry.substitute,
                    entry=entry,
                    dietary_preference=dietary_preference,
                    allergens=allergens,
                )
                if is_safe:
                    compatible_entries.append(entry)

            if compatible_entries:
                conf_weights = {"high": 3, "medium": 2, "low": 1}
                sorted_entries = sorted(
                    compatible_entries,
                    key=lambda e: (
                        2 if context in e.use_cases else (1 if "general" in e.use_cases else 0),
                        conf_weights.get(e.confidence, 1),
                    ),
                    reverse=True,
                )

                results: List[SubstitutionCandidate] = []
                seen = set()
                for entry in sorted_entries[:max_candidates]:
                    if entry.substitute in seen:
                        continue
                    seen.add(entry.substitute)
                    results.append(
                        SubstitutionCandidate(
                            missing_ingredient=missing_ingredient,
                            substitute=entry.substitute,
                            ratio=entry.ratio,
                            confidence=entry.confidence,
                            substitution_type=entry.substitution_type,
                            reason=entry.reason,
                            use_case=context if context != "general" else (entry.use_cases[0] if entry.use_cases else "general"),
                            dietary_compatible=True,
                            safety_status="SAFE",
                            notes=entry.notes,
                            source=entry.source,
                            can_omit=False,
                            shopping_suggestion=f"Add {missing_ingredient} to your grocery list if preferred over {entry.substitute}.",
                        )
                    )
                return results

        # 4. Unknown ingredient with zero validated evidence -> return empty list (no fabrication)
        logger.info(
            f"[SubstitutionService] Evaluated missing item '{missing_ingredient}' (canonical: '{canonical}') independently: "
            f"No reliable validated substitute identified. Preserving integrity without fabrication."
        )
        return []

    def get_substitutions_for_recipe(
        self,
        missing_ingredients: List[str],
        recipe_title: str = "",
        directions: Optional[List[str]] = None,
        dietary_preference: Optional[str] = None,
        allergens: Optional[List[str]] = None,
        max_substitutes_per_item: int = 1,
        pantry_ingredients: Optional[List[str]] = None,
    ) -> List[SubstitutionCandidate]:
        """
        Extracts substitution candidates for all missing ingredients in a recipe.
        Evaluates each missing ingredient independently via dynamic graph search.
        """
        if not missing_ingredients:
            return []

        # If pantry_ingredients not provided, try to fetch current active pantry
        if pantry_ingredients is None:
            try:
                from backend.app.pantry.pantry_store import pantry_store
                pantry_items = pantry_store.get_all(status="available")
                pantry_ingredients = [item.name for item in pantry_items]
            except Exception:
                pantry_ingredients = []

        context = detect_culinary_context(recipe_title, directions or [])
        all_candidates: List[SubstitutionCandidate] = []

        for missing_item in missing_ingredients:
            item_subs = self.get_substitutions_for_ingredient(
                missing_ingredient=missing_item,
                context=context,
                dietary_preference=dietary_preference,
                allergens=allergens,
                max_candidates=max_substitutes_per_item,
                pantry_items=pantry_ingredients,
            )

            if item_subs:
                all_candidates.extend(item_subs)

        return all_candidates

    def generate_substitution_explanation(
        self,
        substitutions: List[SubstitutionCandidate],
    ) -> Optional[str]:
        """
        Generates a human-readable explanation clause detailing suggested alternatives.
        """
        if not substitutions:
            return None

        clauses = []
        for sub in substitutions:
            ratio_str = f" ({sub.ratio})" if sub.ratio else ""
            if sub.substitution_type == "optional_omission":
                clauses.append(f"Missing {sub.missing_ingredient}: Can be omitted as an optional accent.")
            else:
                clauses.append(
                    f"Missing {sub.missing_ingredient}: {sub.substitute} is suggested as a {sub.confidence}-confidence alternative{ratio_str} because {sub.reason.lower()}"
                )

        return " Substitutions: " + " ".join(clauses)


# Global service singleton
substitution_service = SubstitutionService()
