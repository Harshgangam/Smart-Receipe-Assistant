from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Any

from backend.app.config import settings
from backend.app.models.recommendation import (
    ExplanationData,
    RecipeRecommendationItem,
    RecommendationResponse,
)
from backend.app.pantry.pantry_store import pantry_store
from backend.app.recommendation.hybrid_retriever import HybridRetriever, hybrid_retriever
from backend.app.recommendation.normalizer import (
    extract_core_food,
    get_lookup_variants,
    normalize_pantry_ingredient,
    normalize_pantry_list,
    to_singular_form,
)
from backend.app.recommendation.personalizer import evaluate_personalization
from backend.app.recommendation.retriever import RecipeRetriever
from backend.app.recommendation.scorer import (
    calculate_final_score,
    calculate_ims,
    calculate_pus,
    generate_explanation,
    generate_frps_explanation,
)
from backend.app.substitutions.service import substitution_service


class RecommendationEngine:
    """
    Explainable pantry-first recipe recommendation & food-rescue decision engine.
    Executes:
    Pantry Input / Query Text -> Hybrid Semantic FAISS + SQLite Retrieval -> Detail & Metadata Fetch ->
    IMS, PUS, EPS, QUS, DCS, TCS, MIP Scoring -> Food Rescue Priority Scoring (FRPS) ->
    Personalization -> Ranking -> Grounded Explanations.
    """

    def __init__(
        self,
        sqlite_path: Path = settings.SQLITE_INDEX_PATH,
        parquet_path: Path = settings.PARQUET_PATH,
        metadata_path: Optional[Path] = settings.METADATA_DB_PATH,
        ims_weight: float = settings.IMS_WEIGHT,
        pus_weight: float = settings.PUS_WEIGHT,
        candidate_limit: int = settings.CANDIDATE_POOL_LIMIT,
    ):
        self.retriever = RecipeRetriever(sqlite_path, parquet_path, metadata_path)
        self.hybrid_retriever = HybridRetriever(sqlite_path, parquet_path, metadata_path)
        self.ims_weight = ims_weight
        self.pus_weight = pus_weight
        self.candidate_limit = candidate_limit

    def recommend(
        self,
        pantry_ingredients: List[str],
        limit: Optional[int] = 10,
        cuisine: Optional[str] = None,
        dietary_preference: Optional[str] = None,
        allergens: Optional[List[str]] = None,
        max_cooking_time_minutes: Optional[int] = None,
        pantry_items_details: Optional[List[Dict[str, Any]]] = None,
        query_text: Optional[str] = None,
    ) -> RecommendationResponse:
        """
        Processes a user pantry and query text to produce ranked recipe recommendations.
        Executes hybrid FAISS vector search and calculates custom Food Rescue Priority Score (FRPS).
        """
        limit = limit or settings.DEFAULT_RECOMMENDATION_LIMIT

        applied_preferences = {}
        if cuisine:
            applied_preferences["cuisine"] = cuisine
        if dietary_preference:
            applied_preferences["dietary_preference"] = dietary_preference
        if allergens:
            applied_preferences["allergens"] = allergens
        if max_cooking_time_minutes is not None:
            applied_preferences["max_cooking_time_minutes"] = max_cooking_time_minutes

        pantry_risk_map: Dict[str, str] = {}
        pantry_qty_map: Dict[str, float] = {}

        if pantry_items_details:
            for d in pantry_items_details:
                name_clean = d.get("name", "").lower().strip()
                norm_clean = d.get("normalized_name", name_clean).lower().strip()
                risk = d.get("expiry_risk", "low")
                qty = float(d.get("quantity", 1.0))
                pantry_risk_map[name_clean] = risk
                pantry_risk_map[norm_clean] = risk
                pantry_qty_map[name_clean] = qty
                pantry_qty_map[norm_clean] = qty
        else:
            active_pantry = pantry_store.get_all(status="available")
            for item in active_pantry:
                n_clean = item.name.lower().strip()
                norm_clean = item.normalized_name.lower().strip()
                pantry_risk_map[n_clean] = item.expiry_risk
                pantry_risk_map[norm_clean] = item.expiry_risk
                pantry_qty_map[n_clean] = item.quantity
                pantry_qty_map[norm_clean] = item.quantity

        # 1. Ingredient Normalization (Semantic deduplication and canonical resolution)
        normalized_pantry, all_lookup_variants = normalize_pantry_list(pantry_ingredients)
        if not normalized_pantry:
            return RecommendationResponse(
                normalized_pantry=[],
                relevant_pantry=[],
                total_candidates_evaluated=0,
                applied_preferences=applied_preferences,
                recommendations=[],
            )

        variant_to_canonical: Dict[str, str] = {}
        for item in pantry_ingredients:
            canonical = normalize_pantry_ingredient(item)
            if canonical:
                for var in get_lookup_variants(item):
                    variant_to_canonical[var] = canonical
                for var in get_lookup_variants(canonical):
                    variant_to_canonical[var] = canonical

        # 2. Hybrid Candidate Retrieval (FAISS Semantic Vector Search + SQLite Inverted Index)
        search_query = query_text or (" ".join(normalized_pantry) if normalized_pantry else None)
        candidate_ids, details_map, metadata_map = self.hybrid_retriever.retrieve_candidates(
            pantry_variants=all_lookup_variants,
            query_text=search_query,
            limit=self.candidate_limit,
        )

        if not candidate_ids:
            return RecommendationResponse(
                normalized_pantry=normalized_pantry,
                relevant_pantry=[],
                total_candidates_evaluated=0,
                applied_preferences=applied_preferences,
                recommendations=[],
            )

        # 3. Determine Relevant Pantry Set using semantic canonical matching
        relevant_pantry_set: Set[str] = set()
        for r_id in candidate_ids:
            rec = details_map.get(r_id)
            if not rec:
                continue
            for ing in rec["ner"]:
                ing_clean = ing.lower().strip()
                canonical = (
                    variant_to_canonical.get(ing_clean)
                    or variant_to_canonical.get(to_singular_form(ing_clean))
                    or variant_to_canonical.get(extract_core_food(ing_clean))
                    or variant_to_canonical.get(to_singular_form(extract_core_food(ing_clean)))
                )
                if canonical and canonical in normalized_pantry:
                    relevant_pantry_set.add(canonical)

        relevant_pantry_list = [p for p in normalized_pantry if p in relevant_pantry_set]

        # 4. Score Candidates
        scored_candidates: List[RecipeRecommendationItem] = []

        for r_id in candidate_ids:
            rec = details_map.get(r_id)
            if not rec:
                continue

            # Quality Guardrail: Exclude recipes with empty or incomplete stub directions
            raw_dirs = [d.strip() for d in (rec.get("directions") or []) if d and d.strip()]
            if not raw_dirs:
                continue

            # Parse direction paragraphs into distinct step sentences
            parsed_steps: List[str] = []
            for d in raw_dirs:
                cleaned_d = re.sub(r"^\d+[\.\)]\s*", "", d.strip())
                # Split multi-sentence paragraph directions into actionable steps
                sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", cleaned_d)
                for s in sentences:
                    s_clean = s.strip()
                    if s_clean:
                        parsed_steps.append(s_clean)
            if not parsed_steps:
                parsed_steps = raw_dirs

            # Exclude stub recipes that have only 1 step and less than 80 characters (e.g. only "You will need a pie plate.")
            total_dir_len = sum(len(d) for d in parsed_steps)
            if len(parsed_steps) < 2 and total_dir_len < 90:
                continue
            if any(d.lower().startswith("optional") for d in parsed_steps) and total_dir_len < 60:
                continue

            recipe_ner = rec["ner"]
            recipe_meta = metadata_map.get(r_id, {})

            # 4a. Base Scores
            ims, matched, missing = calculate_ims(
                recipe_ner=recipe_ner,
                pantry_variants=all_lookup_variants,
            )

            pus, used_count, total_relevant = calculate_pus(
                recipe_ner=recipe_ner,
                relevant_pantry=relevant_pantry_set,
                pantry_variants_to_canonical=variant_to_canonical,
            )

            base_score = calculate_final_score(
                ims=ims,
                pus=pus,
                ims_weight=self.ims_weight,
                pus_weight=self.pus_weight,
            )

            # 4b. Personalization Evaluation
            personalized_score, pref_matches, pref_explanation = evaluate_personalization(
                base_score=base_score,
                recipe_meta=recipe_meta,
                user_cuisine=cuisine,
                user_dietary=dietary_preference,
                max_cooking_time=max_cooking_time_minutes,
            )

            if personalized_score < 0.0:
                continue

            # 4c. Food Rescue Priority Score (FRPS) Calculation
            # Use deduped total (matched + missing) so singular/plural duplicates
            # like 'tomato'/'tomatoes' don't inflate the ingredient count.
            deduped_total = len(matched) + len(missing)


            # 4d. Missing Ingredients Categorization & Substitutions
            essential_missing = []
            optional_missing = []
            non_essential_keywords = ["salt", "pepper", "oil", "water", "sugar", "butter", "seasoning", "spice"]

            for m in missing:
                m_clean = m.lower()
                if any(kw in m_clean for kw in non_essential_keywords):
                    optional_missing.append(m)
                else:
                    essential_missing.append(m)

            missing_categorized = {
                "essential": essential_missing,
                "optional": optional_missing,
            }

            substitutions = substitution_service.get_substitutions_for_recipe(
                missing_ingredients=missing,
                recipe_title=rec["title"],
                directions=rec["directions"],
                dietary_preference=dietary_preference,
            )
            sub_explanation = substitution_service.generate_substitution_explanation(substitutions)

            # 4e. Explainable AI (XAI) Rationale
            base_explanation = generate_explanation(
                matched_count=len(matched),
                total_recipe_ingredients=deduped_total,
                relevant_used_count=used_count,
                total_relevant_count=total_relevant,
            )

            why_this_recipe = generate_frps_explanation(
                matched_ingredients=matched,
                missing_ingredients=missing,
                total_recipe_ingredients=deduped_total,
                relevant_used_count=used_count,
                total_relevant_count=total_relevant,
                dietary_preference=dietary_preference,
                max_cooking_time=max_cooking_time_minutes,
            )

            explanation_parts = [base_explanation]
            if applied_preferences and pref_explanation != "No specific preferences applied.":
                explanation_parts.append(pref_explanation)
            if sub_explanation:
                explanation_parts.append(sub_explanation.strip())

            full_explanation = " ".join(explanation_parts)

            final_ranking_score = personalized_score

            explanation_data = ExplanationData(
                matched_ingredients=matched,
                missing_ingredients=missing,
                matched_count=len(matched),
                total_recipe_ingredients=deduped_total,
                relevant_pantry_used_count=used_count,
                relevant_pantry_total_count=total_relevant,
                ims=ims,
                pus=pus,
                base_score=base_score,
                final_score=final_ranking_score,

                why_this_recipe=why_this_recipe,
                cuisine_bonus=pref_matches.get("cuisine_bonus", 0.0),
                time_adjustment=pref_matches.get("time_adjustment", 0.0),
                dietary_filter_applied=dietary_preference,
            )

            from backend.app.safety.allergen_guard import allergen_guard
            from backend.app.services.food_waste_optimizer import food_waste_optimizer
            from backend.app.services.shopping_optimizer import shopping_optimizer
            from backend.app.services.sandbox_engine import resolve_recipe_image_url

            # Hard Safety Filter with Semantic Allergen & Dietary Screening
            safety_res = allergen_guard.check_recipe_safety(
                recipe_id=r_id,
                recipe_title=rec["title"],
                ingredients=rec["ingredients"],
                directions=rec["directions"],
                user_allergens=allergens,
                user_diet=dietary_preference,
                recipe_ner=recipe_ner,
            )
            if safety_res.is_blocked:
                continue

            img_url = resolve_recipe_image_url(
                title=rec["title"],
                cuisine=recipe_meta.get("cuisine"),
                recipe_id=r_id,
                ner=recipe_ner,
                ingredients=rec["ingredients"],
                dietary_preference=dietary_preference,
            )
            missing_cost = sum(shopping_optimizer.estimate_item_cost(item).estimated_package_cost for item in missing)

            waste_res = food_waste_optimizer.optimize_recipe_ranking(
                recipe_id=r_id,
                title=rec["title"],
                matched_ingredients=matched,
                missing_ingredients=missing,
                pantry_expiry_map=pantry_risk_map,
                total_pantry_count=len(normalized_pantry),
                estimated_missing_cost=missing_cost,
            )

            scored_candidates.append(
                RecipeRecommendationItem(
                    recipe_id=r_id,
                    title=rec["title"],
                    ingredients=rec["ingredients"],
                    directions=parsed_steps,
                    link=rec["link"],
                    source=rec["source"],
                    ner=recipe_ner,
                    matched_ingredients=matched,
                    missing_ingredients=missing,
                    missing_count=len(missing),
                    missing_categorized=missing_categorized,
                    can_prepare_without_missing=len(essential_missing) <= 1,
                    substitutions=substitutions,
                    ims=ims,
                    pus=pus,
                    recommendation_score=final_ranking_score,

                    image_url=img_url,
                    safety_status=safety_res.status,
                    safety_reasons=safety_res.reasons or safety_res.warnings,
                    estimated_missing_cost=round(missing_cost, 2),
                    food_waste_score=waste_res.composite_waste_score,

                    why_this_recipe=why_this_recipe,
                    explanation=full_explanation,
                    explanation_data=explanation_data,
                    cuisine=recipe_meta.get("cuisine"),
                    cuisine_confidence=recipe_meta.get("cuisine_confidence"),
                    dietary_compatibility=recipe_meta.get("dietary_compatibility"),
                    dietary_confidence=recipe_meta.get("dietary_confidence"),
                    estimated_time_minutes=recipe_meta.get("estimated_time_minutes"),
                    time_confidence=recipe_meta.get("time_confidence"),
                    preference_matches=pref_matches if applied_preferences else {},
                    preference_explanation=pref_explanation if applied_preferences else None,
                )
            )

        # 5. Deterministic Ranking
        scored_candidates.sort(
            key=lambda x: (
                -x.recommendation_score,
                -x.ims,
                -x.pus,
                x.recipe_id,
            )
        )

        top_recommendations = scored_candidates[:limit]

        # 6. Guaranteed Collision-Free Unique & Relatable Image Assignment
        used_recommendation_images: Set[str] = set()
        for item in top_recommendations:
            item.image_url = resolve_recipe_image_url(
                title=item.title,
                cuisine=item.cuisine,
                recipe_id=item.recipe_id,
                used_urls=used_recommendation_images,
                ner=item.ner,
                ingredients=item.ingredients,
                dietary_preference=dietary_preference,
            )
            used_recommendation_images.add(item.image_url)

        return RecommendationResponse(
            normalized_pantry=normalized_pantry,
            relevant_pantry=relevant_pantry_list,
            total_candidates_evaluated=len(scored_candidates),
            applied_preferences=applied_preferences,
            recommendations=top_recommendations,
        )
