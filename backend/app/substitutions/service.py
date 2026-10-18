import logging
import re
from typing import Dict, List, Optional, Set, Tuple

from backend.app.safety.allergen_guard import ALLERGEN_TAXONOMY
from backend.app.substitutions.context import detect_culinary_context
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
    Intelligent substitution engine providing context-aware, dietary-filtered,
    and allergen-hardlocked ingredient alternatives for missing recipe ingredients.
    Features independent per-ingredient evaluation, canonical normalization,
    and controlled fallback with omission/shopping guidance.
    """

    def __init__(self, database: Optional[List[SubstitutionEntry]] = None):
        self.database = database or SUBSTITUTION_DATABASE
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
        entry: Optional[SubstitutionEntry],
        dietary_preference: Optional[str] = None,
        allergens: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """
        Deterministic Allergen and Dietary Hard-Lock Filter.
        Guarantees that neither knowledge base entries nor fallbacks bypass safety constraints.
        Returns: (is_safe, safety_status) -> where safety_status is 'SAFE' | 'BLOCKED'
        """
        cand_lower = candidate_name.lower().strip()
        user_diet = (dietary_preference or "").lower().strip()
        user_algs = [a.lower().strip() for a in (allergens or [])]

        # 1. Check Allergens
        if user_algs:
            # Check entry explicit allergens list
            if entry and entry.allergens:
                for alg in user_algs:
                    if alg in [a.lower() for a in entry.allergens]:
                        logger.info(f"[Safety Hard-Lock] Rejected '{candidate_name}': Contains allergen '{alg}'")
                        return False, "BLOCKED"

            # Check allergen taxonomy keywords against candidate name, respecting plant-based dairy alternatives
            plant_milk_cheese = ["soy milk", "almond milk", "oat milk", "coconut milk", "plant-based", "vegan", "cashew"]
            for alg in user_algs:
                if alg == "dairy" and any(p in cand_lower for p in plant_milk_cheese):
                    continue
                tax_keywords = ALLERGEN_TAXONOMY.get(alg, [alg])
                for kw in tax_keywords:
                    if kw in cand_lower:
                        logger.info(f"[Safety Hard-Lock] Rejected '{candidate_name}': Matches allergen '{alg}' keyword '{kw}'")
                        return False, "BLOCKED"

        # 2. Check Dietary Restrictions
        if user_diet == "vegan":
            if entry and "vegan" not in entry.dietary_compatibility:
                logger.info(f"[Safety Hard-Lock] Rejected '{candidate_name}': Not compatible with vegan diet")
                return False, "BLOCKED"
            # If candidate is explicitly labeled plant-based or known plant milk, it is vegan
            plant_exceptions = ["soy milk", "almond milk", "oat milk", "coconut milk", "vegan", "plant-based", "cashew mozzarella"]
            if not any(pe in cand_lower for pe in plant_exceptions):
                non_vegan = ["milk", "butter", "cheese", "egg", "cream", "yogurt", "paneer", "honey", "pork", "beef", "chicken", "meat", "salami", "chorizo", "pepperoni", "gelatin", "whey"]
                if any(nv in cand_lower for nv in non_vegan):
                    logger.info(f"[Safety Hard-Lock] Rejected '{candidate_name}': Violates vegan restriction")
                    return False, "BLOCKED"

        elif user_diet == "vegetarian":
            if entry and ("vegetarian" not in entry.dietary_compatibility and "vegan" not in entry.dietary_compatibility):
                logger.info(f"[Safety Hard-Lock] Rejected '{candidate_name}': Not compatible with vegetarian diet")
                return False, "BLOCKED"
            plant_meat_exceptions = ["tempeh", "tofu", "vegan", "plant-based", "seitan", "lentil", "lentils"]
            if not any(pe in cand_lower for pe in plant_meat_exceptions):
                meat_keywords = ["chicken", "beef", "pork", "lamb", "bacon", "salmon", "shrimp", "fish", "turkey", "salami", "chorizo", "pepperoni", "prosciutto", "pancetta"]
                if any(m in cand_lower for m in meat_keywords):
                    logger.info(f"[Safety Hard-Lock] Rejected '{candidate_name}': Violates vegetarian restriction")
                    return False, "BLOCKED"

        return True, "SAFE"

    def get_substitutions_for_ingredient(
        self,
        missing_ingredient: str,
        context: str = "general",
        dietary_preference: Optional[str] = None,
        allergens: Optional[List[str]] = None,
        max_candidates: int = 2,
    ) -> List[SubstitutionCandidate]:
        """
        Finds appropriate substitution candidates for a single missing ingredient independently.
        Applies canonical normalization, context prioritization, and deterministic safety hard-locks.
        """
        raw_entries = self.lookup_raw_entries(missing_ingredient)
        if not raw_entries:
            logger.debug(f"[SubstitutionService] No database/graph entry for '{missing_ingredient}'.")
            return []

        # Filter strictly with hard-lock safety
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

        if not compatible_entries:
            logger.info(f"[SubstitutionService] All candidates for '{missing_ingredient}' filtered out by safety hard-lock.")
            return []

        # Sort/Prioritize by context match, then confidence
        conf_weights = {"high": 3, "medium": 2, "low": 1}

        def score_entry(e: SubstitutionEntry):
            context_match = 1 if (context in e.use_cases or "general" in e.use_cases) else 0
            exact_context_match = 2 if context in e.use_cases else 0
            conf_score = conf_weights.get(e.confidence, 1)
            return (exact_context_match, context_match, conf_score)

        sorted_entries = sorted(compatible_entries, key=score_entry, reverse=True)

        results: List[SubstitutionCandidate] = []
        seen_substitutes = set()

        for entry in sorted_entries[:max_candidates]:
            if entry.substitute in seen_substitutes:
                continue
            seen_substitutes.add(entry.substitute)

            canonical = resolve_canonical_ingredient(missing_ingredient)
            can_omit = canonical in OPTIONAL_GARNISH_INGREDIENTS

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
                    can_omit=can_omit,
                    shopping_suggestion=f"Add {missing_ingredient} to your grocery list if preferred over {entry.substitute}.",
                )
            )

        return results

    def get_substitutions_for_recipe(
        self,
        missing_ingredients: List[str],
        recipe_title: str = "",
        directions: Optional[List[str]] = None,
        dietary_preference: Optional[str] = None,
        allergens: Optional[List[str]] = None,
        max_substitutes_per_item: int = 1,
    ) -> List[SubstitutionCandidate]:
        """
        Extracts substitution candidates for all missing ingredients in a recommended recipe.
        Evaluates each missing ingredient independently.
        """
        if not missing_ingredients:
            return []

        context = detect_culinary_context(recipe_title, directions or [])
        all_candidates: List[SubstitutionCandidate] = []

        for missing_item in missing_ingredients:
            item_subs = self.get_substitutions_for_ingredient(
                missing_ingredient=missing_item,
                context=context,
                dietary_preference=dietary_preference,
                allergens=allergens,
                max_candidates=max_substitutes_per_item,
            )

            if item_subs:
                all_candidates.extend(item_subs)
            else:
                # Controlled context-aware fallback & omission check
                canonical = resolve_canonical_ingredient(missing_item)
                can_omit = canonical in OPTIONAL_GARNISH_INGREDIENTS
                is_pivotal = canonical in STRUCTURAL_PIVOTAL_INGREDIENTS

                if can_omit:
                    all_candidates.append(
                        SubstitutionCandidate(
                            missing_ingredient=missing_item,
                            substitute="Optional omission",
                            ratio=None,
                            confidence="medium",
                            substitution_type="optional_omission",
                            reason=f"{missing_item.capitalize()} serves primarily as a decorative garnish or accent and can be omitted without compromising the core dish structure.",
                            use_case=context,
                            dietary_compatible=True,
                            safety_status="SAFE",
                            can_omit=True,
                            notes="Omit without flavor balance issues.",
                            source="Culinary Institute of America",
                            shopping_suggestion=f"Add {missing_item} to shopping list for full presentation.",
                        )
                    )
                else:
                    logger.info(
                        f"[SubstitutionService] Evaluated missing item '{missing_item}' (canonical: '{canonical}') independently: "
                        f"No reliable validated substitute identified. Preserving integrity without fabrication."
                    )

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
