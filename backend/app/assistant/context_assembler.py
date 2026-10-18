from typing import Dict, List, Optional, Set
from backend.app.assistant.models import StructuredRecipeContext
from backend.app.config import settings
from backend.app.recommendation.scorer import (
    calculate_final_score,
    calculate_ims,
    calculate_pus,
)
from backend.app.recommendation.personalizer import evaluate_personalization
from backend.app.recommendation.retriever import RecipeRetriever
from backend.app.substitutions.service import substitution_service
from backend.app.recommendation.normalizer import (
    get_lookup_variants,
    normalize_pantry_ingredient,
    normalize_pantry_list,
    to_singular_form,
)
from backend.app.services.sandbox_engine import resolve_recipe_image_url



class ContextAssembler:
    """
    Assembles an authoritative, structured recipe context packet for Entity-Grounded RAG.
    Extracts recipe details from Parquet, derived metadata from SQLite, computes pantry alignment,
    and resolves curated substitutions for missing ingredients.
    """

    def __init__(self, retriever: Optional[RecipeRetriever] = None):
        self.retriever = retriever or RecipeRetriever(
            sqlite_path=settings.SQLITE_INDEX_PATH,
            parquet_path=settings.PARQUET_PATH,
            metadata_path=settings.METADATA_DB_PATH,
        )

    def assemble_context(
        self,
        recipe_id: int,
        pantry_ingredients: Optional[List[str]] = None,
        cuisine: Optional[str] = None,
        dietary_preference: Optional[str] = None,
        max_cooking_time_minutes: Optional[int] = None,
    ) -> Optional[StructuredRecipeContext]:
        """
        Retrieves and compiles all verified ground-truth data for the given recipe and user session.
        """
        if not pantry_ingredients:
            try:
                from backend.app.storage.pantry_store import pantry_store
                active_items = pantry_store.get_all(status="available")
                pantry_ingredients = [item.name for item in active_items]
            except Exception:
                pantry_ingredients = []
        pantry_ingredients = pantry_ingredients or []

        # 1. Fetch raw recipe details and derived metadata
        details_map = self.retriever.fetch_recipe_details([recipe_id])
        rec = details_map.get(recipe_id)
        if not rec:
            return None

        metadata_map = self.retriever.fetch_recipe_metadata([recipe_id])
        recipe_meta = metadata_map.get(recipe_id, {})

        recipe_ner: List[str] = rec.get("ner", [])

        # 2. Ingredient Normalization & Matching
        normalized_pantry, all_lookup_variants = normalize_pantry_list(pantry_ingredients)
        variant_to_canonical: Dict[str, str] = {}
        for item in pantry_ingredients:
            norm = normalize_pantry_ingredient(item)
            if norm:
                canonical = to_singular_form(norm) if to_singular_form(norm) else norm
                for var in get_lookup_variants(norm):
                    variant_to_canonical[var] = canonical

        relevant_pantry_set: Set[str] = set()
        for ing in recipe_ner:
            canonical = variant_to_canonical.get(ing)
            if canonical and canonical in normalized_pantry:
                relevant_pantry_set.add(canonical)

        # 3. Base IMS, PUS, and Score
        ims, matched, missing = calculate_ims(
            recipe_ner=recipe_ner,
            pantry_variants=all_lookup_variants,
        )

        pus, _, _ = calculate_pus(
            recipe_ner=recipe_ner,
            relevant_pantry=relevant_pantry_set,
            pantry_variants_to_canonical=variant_to_canonical,
        )

        base_score = calculate_final_score(
            ims=ims,
            pus=pus,
            ims_weight=settings.IMS_WEIGHT,
            pus_weight=settings.PUS_WEIGHT,
        )

        # 4. Personalization Adjustments
        personalized_score, _, _ = evaluate_personalization(
            base_score=base_score,
            recipe_meta=recipe_meta,
            user_cuisine=cuisine,
            user_dietary=dietary_preference,
            max_cooking_time=max_cooking_time_minutes,
        )
        final_score = max(0.0, personalized_score)

        # 5. Resolve Curated Knowledge Base Substitutions
        raw_subs = substitution_service.get_substitutions_for_recipe(
            missing_ingredients=missing,
            recipe_title=rec["title"],
            directions=rec["directions"],
            dietary_preference=dietary_preference,
        )
        subs_dict_list = [s.model_dump() for s in raw_subs]

        return StructuredRecipeContext(
            recipe_id=recipe_id,
            title=rec["title"],
            ingredients=rec["ingredients"],
            directions=rec["directions"],
            ner=recipe_ner,
            cuisine=recipe_meta.get("cuisine"),
            cuisine_confidence=recipe_meta.get("cuisine_confidence"),
            dietary_compatibility=recipe_meta.get("dietary_compatibility"),
            dietary_confidence=recipe_meta.get("dietary_confidence"),
            estimated_time_minutes=recipe_meta.get("estimated_time_minutes"),
            time_confidence=recipe_meta.get("time_confidence"),
            matched_ingredients=matched,
            missing_ingredients=missing,
            ims=ims,
            pus=pus,
            recommendation_score=final_score,
            substitutions=subs_dict_list,
            dietary_preference_applied=dietary_preference,
            cuisine_preference_applied=cuisine,
            max_cooking_time_applied=max_cooking_time_minutes,
            image_url=resolve_recipe_image_url(
                title=rec["title"],
                cuisine=recipe_meta.get("cuisine"),
                recipe_id=recipe_id,
            ),
        )

    def format_context_for_prompt(self, context: StructuredRecipeContext) -> str:
        """
        Formats structured context into a clean, human-readable markdown block for LLM prompt injection.
        """
        lines = []
        lines.append("=== RECIPE CONTEXT (AUTHORITATIVE GROUND TRUTH) ===")
        lines.append(f"Recipe ID: {context.recipe_id}")
        lines.append(f"Title: {context.title}")
        lines.append(
            f"Cuisine: {context.cuisine or 'Unclassified'} (Confidence: {context.cuisine_confidence or 'None'})"
        )
        lines.append(
            f"Dietary Compatibility: {context.dietary_compatibility or 'standard'} (Confidence: {context.dietary_confidence or 'None'})"
        )
        time_str = (
            f"{context.estimated_time_minutes} minutes"
            if context.estimated_time_minutes
            else "Unspecified / Not stated in directions"
        )
        lines.append(f"Estimated Active Cooking Time: {time_str}")

        lines.append("\n=== PANTRY MATCH & SCORING ===")
        lines.append(
            f"Matched Pantry Ingredients ({len(context.matched_ingredients)}): {', '.join(context.matched_ingredients) if context.matched_ingredients else 'None'}"
        )
        lines.append(
            f"Missing Recipe Ingredients ({len(context.missing_ingredients)}): {', '.join(context.missing_ingredients) if context.missing_ingredients else 'None'}"
        )
        lines.append(f"Ingredient Match Score (IMS): {context.ims:.1f}%")
        lines.append(f"Pantry Utilization Score (PUS): {context.pus:.1f}%")
        lines.append(f"Recommendation Score: {context.recommendation_score:.1f}")

        lines.append("\n=== CURATED KNOWLEDGE BASE SUBSTITUTIONS (VERIFIED) ===")
        if context.substitutions:
            for sub in context.substitutions:
                ratio_str = f" (Ratio: {sub['ratio']})" if sub.get("ratio") else ""
                lines.append(
                    f"- Missing '{sub['missing_ingredient']}': Use '{sub['substitute']}'{ratio_str} [Confidence: {sub['confidence']}]. Reason: {sub['reason']}"
                )
        else:
            lines.append("No verified substitutions found for missing ingredients in this recipe.")

        lines.append("\n=== RAW INGREDIENTS LIST ===")
        for idx, ing in enumerate(context.ingredients, 1):
            lines.append(f"{idx}. {ing}")

        lines.append("\n=== COOKING DIRECTIONS ===")
        for idx, step in enumerate(context.directions, 1):
            lines.append(f"Step {idx}: {step}")

        lines.append("==================================================")
        return "\n".join(lines)


# Global context assembler instance
context_assembler = ContextAssembler()
