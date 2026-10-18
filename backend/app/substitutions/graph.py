"""
backend/app/substitutions/graph.py

Novelty 1: Dynamic Smart Substitution Knowledge Graph
Uses NetworkX to build an explicit ingredient knowledge graph with rich attributes
and weighted relationships (flavor, texture, acidity, cooking role, diet tags, allergens).
"""

import logging
import networkx as nx
from typing import Any, Dict, List, Optional, Set, Tuple

from backend.app.safety.allergen_guard import ALLERGEN_TAXONOMY
from backend.app.substitutions.knowledge_base import SUBSTITUTION_DATABASE
from backend.app.substitutions.normalizer import resolve_canonical_ingredient

logger = logging.getLogger(__name__)


class IngredientSubstitutionGraph:
    """
    Graph-based substitution engine representing ingredient nodes & culinary relationship edges.
    Supports single-node substitutions, functional combinations, and safe fallbacks.
    """

    def __init__(self):
        self.graph = nx.MultiDiGraph()
        self._build_graph()

    def _build_graph(self):
        # 1. Base Nodes with Attributes
        ingredients_attributes: Dict[str, Dict[str, Any]] = {
            "butter": {"flavor": "rich_creamy", "texture": "solid_fat", "acidity": 0.0, "role": "fat_moisture", "diet": ["vegetarian"], "allergens": ["dairy"]},
            "margarine": {"flavor": "neutral_salty", "texture": "solid_fat", "acidity": 0.0, "role": "fat_moisture", "diet": ["vegetarian", "vegan"], "allergens": []},
            "olive oil": {"flavor": "fruity_savory", "texture": "liquid_fat", "acidity": 0.0, "role": "fat_frying", "diet": ["vegetarian", "vegan"], "allergens": []},
            "vegetable oil": {"flavor": "neutral", "texture": "liquid_fat", "acidity": 0.0, "role": "fat_frying", "diet": ["vegetarian", "vegan"], "allergens": []},
            "canola oil": {"flavor": "neutral", "texture": "liquid_fat", "acidity": 0.0, "role": "fat_frying", "diet": ["vegetarian", "vegan"], "allergens": []},
            "milk": {"flavor": "creamy_mild", "texture": "liquid", "acidity": 0.1, "role": "liquid_moisture", "diet": ["vegetarian"], "allergens": ["dairy"]},
            "soy milk": {"flavor": "neutral_nutty", "texture": "liquid", "acidity": 0.1, "role": "liquid_moisture", "diet": ["vegetarian", "vegan"], "allergens": ["soy"]},
            "almond milk": {"flavor": "nutty_sweet", "texture": "thin_liquid", "acidity": 0.1, "role": "liquid_moisture", "diet": ["vegetarian", "vegan"], "allergens": ["tree_nuts"]},
            "oat milk": {"flavor": "creamy_oat", "texture": "creamy_liquid", "acidity": 0.1, "role": "liquid_thickener", "diet": ["vegetarian", "vegan"], "allergens": []},
            "heavy cream": {"flavor": "rich_fat", "texture": "viscous_fat", "acidity": 0.1, "role": "fat_thickener", "diet": ["vegetarian"], "allergens": ["dairy"]},
            "coconut cream": {"flavor": "coconut_sweet", "texture": "viscous_fat", "acidity": 0.1, "role": "fat_thickener", "diet": ["vegetarian", "vegan"], "allergens": ["coconut"]},
            "sour cream": {"flavor": "tangy_cultured", "texture": "thick_cream", "acidity": 0.6, "role": "acid_fat", "diet": ["vegetarian"], "allergens": ["dairy"]},
            "plain greek yogurt": {"flavor": "tangy_cultured", "texture": "thick_cream", "acidity": 0.6, "role": "acid_fat", "diet": ["vegetarian"], "allergens": ["dairy"]},
            "buttermilk": {"flavor": "tangy_acidic", "texture": "thin_cultured", "acidity": 0.8, "role": "acid_leavener", "diet": ["vegetarian"], "allergens": ["dairy"]},
            "lemon juice": {"flavor": "citrus_tart", "texture": "liquid", "acidity": 0.9, "role": "acid_brightener", "diet": ["vegetarian", "vegan"], "allergens": []},
            "lime juice": {"flavor": "citrus_tart", "texture": "liquid", "acidity": 0.9, "role": "acid_brightener", "diet": ["vegetarian", "vegan"], "allergens": []},
            "white vinegar": {"flavor": "sharp_acidic", "texture": "liquid", "acidity": 1.0, "role": "acid_leavener", "diet": ["vegetarian", "vegan"], "allergens": []},
            "apple cider vinegar": {"flavor": "fruity_tart", "texture": "liquid", "acidity": 0.85, "role": "acid_flavor", "diet": ["vegetarian", "vegan"], "allergens": []},
            "egg": {"flavor": "rich_savory", "texture": "viscous_binder", "acidity": 0.0, "role": "binder_leavener", "diet": ["vegetarian"], "allergens": ["egg"]},
            "flax egg": {"flavor": "nutty_grain", "texture": "gelatinous_binder", "acidity": 0.0, "role": "binder_moisture", "diet": ["vegetarian", "vegan"], "allergens": []},
            "applesauce": {"flavor": "sweet_apple", "texture": "puree", "acidity": 0.3, "role": "moisture_binder", "diet": ["vegetarian", "vegan"], "allergens": []},
            "garlic": {"flavor": "pungent_allium", "texture": "solid", "acidity": 0.1, "role": "aromatic_flavor", "diet": ["vegetarian", "vegan"], "allergens": []},
            "garlic powder": {"flavor": "pungent_allium", "texture": "powder", "acidity": 0.1, "role": "aromatic_flavor", "diet": ["vegetarian", "vegan"], "allergens": []},
            "onion": {"flavor": "sweet_allium", "texture": "solid", "acidity": 0.1, "role": "aromatic_base", "diet": ["vegetarian", "vegan"], "allergens": []},
            "shallots": {"flavor": "sweet_delicate_allium", "texture": "solid", "acidity": 0.1, "role": "aromatic_base", "diet": ["vegetarian", "vegan"], "allergens": []},
            "green onion": {"flavor": "fresh_allium", "texture": "solid", "acidity": 0.1, "role": "aromatic_garnish", "diet": ["vegetarian", "vegan"], "allergens": []},
            "chicken broth": {"flavor": "savory_poultry", "texture": "liquid", "acidity": 0.0, "role": "savory_liquid", "diet": ["non_vegetarian"], "allergens": []},
            "vegetable broth": {"flavor": "savory_mirepoix", "texture": "liquid", "acidity": 0.0, "role": "savory_liquid", "diet": ["vegetarian", "vegan"], "allergens": []},
            "parmesan cheese": {"flavor": "umami_salty", "texture": "hard_grated", "acidity": 0.2, "role": "umami_garnish", "diet": ["vegetarian"], "allergens": ["dairy"]},
            "parmesan": {"flavor": "umami_salty", "texture": "hard_grated", "acidity": 0.2, "role": "umami_garnish", "diet": ["vegetarian"], "allergens": ["dairy"]},
            "nutritional yeast": {"flavor": "cheesy_nutty", "texture": "flakes", "acidity": 0.1, "role": "umami_garnish", "diet": ["vegetarian", "vegan"], "allergens": []},
            "cornstarch": {"flavor": "neutral", "texture": "powder", "acidity": 0.0, "role": "thickener", "diet": ["vegetarian", "vegan"], "allergens": []},
            "all-purpose flour": {"flavor": "neutral_grain", "texture": "powder", "acidity": 0.0, "role": "structure_thickener", "diet": ["vegetarian", "vegan"], "allergens": ["gluten"]},
            "paneer": {"flavor": "mild_creamy", "texture": "soft_solid", "acidity": 0.0, "role": "protein_main", "diet": ["vegetarian"], "allergens": ["dairy"]},
            "tofu": {"flavor": "neutral", "texture": "soft_solid", "acidity": 0.0, "role": "protein_main", "diet": ["vegetarian", "vegan"], "allergens": ["soy"]},
            # Added Key Culinary Staples & Pizza / Skillet Essentials
            "mushroom": {"flavor": "earthy_umami", "texture": "firm_tender_chew", "acidity": 0.0, "role": "savory_bulk_umami", "diet": ["vegetarian", "vegan"], "allergens": []},
            "portabello mushrooms": {"flavor": "earthy_umami", "texture": "dense_meaty", "acidity": 0.0, "role": "savory_bulk_umami", "diet": ["vegetarian", "vegan"], "allergens": []},
            "cremini or baby bella mushrooms": {"flavor": "earthy_umami", "texture": "firm_tender_chew", "acidity": 0.0, "role": "savory_bulk_umami", "diet": ["vegetarian", "vegan"], "allergens": []},
            "green bell pepper": {"flavor": "sweet_capsicum", "texture": "crisp_tender", "acidity": 0.1, "role": "aromatic_vegetable_crunch", "diet": ["vegetarian", "vegan"], "allergens": []},
            "red bell pepper or yellow bell pepper": {"flavor": "sweet_capsicum", "texture": "crisp_tender", "acidity": 0.1, "role": "aromatic_vegetable_crunch", "diet": ["vegetarian", "vegan"], "allergens": []},
            "poblano pepper": {"flavor": "earthy_capsicum", "texture": "crisp_tender", "acidity": 0.1, "role": "aromatic_vegetable_crunch", "diet": ["vegetarian", "vegan"], "allergens": []},
            "pepperoni": {"flavor": "spicy_smoky_umami", "texture": "chewy_cured", "acidity": 0.1, "role": "cured_fat_protein", "diet": ["non_vegetarian"], "allergens": []},
            "salami or chorizo": {"flavor": "spicy_smoky_umami", "texture": "chewy_cured", "acidity": 0.1, "role": "cured_fat_protein", "diet": ["non_vegetarian"], "allergens": []},
            "turkey pepperoni": {"flavor": "spicy_smoky_umami", "texture": "chewy_cured", "acidity": 0.1, "role": "cured_fat_protein", "diet": ["non_vegetarian"], "allergens": []},
            "mozzarella": {"flavor": "mild_buttery_creamy", "texture": "elastic_melt", "acidity": 0.1, "role": "melting_cheese", "diet": ["vegetarian"], "allergens": ["dairy"]},
            "mozzarella cheese": {"flavor": "mild_buttery_creamy", "texture": "elastic_melt", "acidity": 0.1, "role": "melting_cheese", "diet": ["vegetarian"], "allergens": ["dairy"]},
            "provolone cheese": {"flavor": "mild_buttery_creamy", "texture": "elastic_melt", "acidity": 0.1, "role": "melting_cheese", "diet": ["vegetarian"], "allergens": ["dairy"]},
            "monterey jack cheese or mild cheddar": {"flavor": "mild_buttery_creamy", "texture": "smooth_melt", "acidity": 0.1, "role": "melting_cheese", "diet": ["vegetarian"], "allergens": ["dairy"]},
            "ground beef": {"flavor": "savory_beef", "texture": "crumbled_protein", "acidity": 0.0, "role": "protein_main", "diet": ["non_vegetarian"], "allergens": []},
            "ground turkey or ground chicken": {"flavor": "savory_poultry", "texture": "crumbled_protein", "acidity": 0.0, "role": "protein_main", "diet": ["non_vegetarian"], "allergens": []},
            "banana": {"flavor": "sweet_fruit", "texture": "dense_puree", "acidity": 0.2, "role": "moisture_binder_sweetener", "diet": ["vegetarian", "vegan"], "allergens": []},
        }

        for name, attrs in ingredients_attributes.items():
            self.graph.add_node(name, **attrs)

        # 2. Add Edges from Database
        for entry in SUBSTITUTION_DATABASE:
            orig = entry.original_ingredient.lower().strip()
            sub = entry.substitute.lower().strip()

            # Ensure nodes exist
            if not self.graph.has_node(orig):
                self.graph.add_node(
                    orig,
                    flavor="general",
                    texture="general",
                    acidity=0.0,
                    role="culinary",
                    diet=["vegetarian", "vegan"] if "non_vegetarian" not in entry.dietary_compatibility else ["non_vegetarian"],
                    allergens=[],
                )
            if not self.graph.has_node(sub):
                self.graph.add_node(
                    sub,
                    flavor=entry.flavor_notes or "general",
                    texture=entry.texture_notes or "general",
                    acidity=0.0,
                    role="culinary",
                    diet=entry.dietary_compatibility or ["vegetarian", "vegan"],
                    allergens=entry.allergens or [],
                )

            self.graph.add_edge(
                orig,
                sub,
                key="SUBSTITUTES",
                relation_type="SUBSTITUTES",
                ratio=entry.ratio,
                confidence=entry.confidence,
                substitution_type=entry.substitution_type,
                reason=entry.reason,
                use_cases=entry.use_cases,
                dietary_compatibility=entry.dietary_compatibility,
                allergens=entry.allergens,
            )

        # 3. Add Functional Multi-Ingredient Combination Rules
        self.functional_combinations: Dict[str, Dict[str, Any]] = {
            "buttermilk": {
                "components": ["milk", "lemon juice"],
                "ratio": "1 cup milk + 1 tbsp lemon juice",
                "reason": "Milk combined with acid reproduces buttermilk's functional acidity and leavening action.",
                "diet": ["vegetarian"],
                "allergens": ["dairy"],
            },
            "heavy cream": {
                "components": ["milk", "butter"],
                "ratio": "3/4 cup milk + 1/4 cup melted butter",
                "reason": "Whisking milk with butter reconstructs the high fat ratio of heavy cream for sauces.",
                "diet": ["vegetarian"],
                "allergens": ["dairy"],
            },
            "sour cream": {
                "components": ["silken tofu", "lemon juice"],
                "ratio": "1 cup silken tofu + 1 tbsp lemon juice",
                "reason": "Pureed silken tofu blended with citrus creates smooth dairy-free acidity.",
                "diet": ["vegetarian", "vegan"],
                "allergens": ["soy"],
            },
            "pepperoni": {
                "components": ["sun-dried tomatoes", "kalamata olives", "smoked paprika"],
                "ratio": "1:1 blend",
                "reason": "Chewy sun-dried tomatoes combined with salty olives and smoked paprika replicate cured savory chew and spiced fat notes without meat.",
                "diet": ["vegetarian", "vegan"],
                "allergens": [],
            },
        }

    def calculate_substitution_score(
        self,
        orig_node: str,
        cand_node: str,
        context: str = "general",
        user_diet: Optional[str] = None,
        user_allergens: Optional[List[str]] = None,
    ) -> float:
        """
        Calculates quantitative SubstitutionScore:
        SubstitutionScore = flavor_sim + texture_sim + role_sim + diet_fit - allergen_risk
        """
        if not self.graph.has_node(orig_node) or not self.graph.has_node(cand_node):
            return 50.0

        o_attr = self.graph.nodes[orig_node]
        c_attr = self.graph.nodes[cand_node]

        # 1. Deterministic Allergen Hard-Lock Violation
        if user_allergens:
            user_algs_clean = [a.lower().strip() for a in user_allergens]
            c_allergens = [a.lower().strip() for a in c_attr.get("allergens", [])]
            cand_name_lower = cand_node.lower()

            for alg in user_algs_clean:
                # Check explicit node allergen tag
                if alg in c_allergens:
                    logger.debug(f"[Graph] Hard-lock allergen rejection: {cand_node} contains allergen tag {alg}")
                    return 0.0

                # Check taxonomy tokens against candidate name
                taxonomy_tokens = ALLERGEN_TAXONOMY.get(alg, [alg])
                for tok in taxonomy_tokens:
                    if tok in cand_name_lower:
                        logger.debug(f"[Graph] Hard-lock allergen rejection: {cand_node} contains token {tok} for allergen {alg}")
                        return 0.0

        # 2. Deterministic Dietary Hard-Lock Check
        diet_fit = 25.0
        if user_diet:
            diet_str = user_diet.lower().strip()
            c_diet = c_attr.get("diet", ["vegetarian", "vegan"])
            cand_name_lower = cand_node.lower()

            if diet_str == "vegan":
                if "vegan" not in c_diet:
                    return 0.0
                non_vegan_kws = ["milk", "cheese", "butter", "egg", "cream", "yogurt", "pork", "beef", "chicken", "meat", "chorizo", "salami", "pepperoni", "honey"]
                if any(kw in cand_name_lower for kw in non_vegan_kws):
                    return 0.0
            elif diet_str == "vegetarian":
                if "vegetarian" not in c_diet and "vegan" not in c_diet:
                    return 0.0
                meat_kws = ["pork", "beef", "chicken", "meat", "chorizo", "salami", "pepperoni", "turkey pepperoni", "turkey", "fish", "anchovy"]
                if any(kw in cand_name_lower for kw in meat_kws):
                    return 0.0

        # 3. Attribute Similarities
        flavor_sim = 25.0 if o_attr.get("flavor") == c_attr.get("flavor") else 15.0
        texture_sim = 25.0 if o_attr.get("texture") == c_attr.get("texture") else 15.0
        role_sim = 25.0 if o_attr.get("role") == c_attr.get("role") else 15.0

        score = flavor_sim + texture_sim + role_sim + diet_fit
        return min(100.0, max(0.0, score))

    def find_substitutes(
        self,
        missing_ingredient: str,
        pantry_items: Optional[List[str]] = None,
        context: str = "general",
        dietary_preference: Optional[str] = None,
        user_allergens: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Queries graph neighbors & functional combinations for optimal substitutes.
        Normalizes ingredient token before traversal and logs decision pathway.
        """
        pantry_items = pantry_items or []
        pantry_set = {p.lower().strip() for p in pantry_items}

        canonical = resolve_canonical_ingredient(missing_ingredient)
        raw_norm = missing_ingredient.lower().strip()

        lookup_keys = [canonical]
        if raw_norm != canonical and raw_norm not in lookup_keys:
            lookup_keys.append(raw_norm)

        candidates: List[Dict[str, Any]] = []

        # 1. Check functional combinations
        for k in lookup_keys:
            if k in self.functional_combinations:
                func = self.functional_combinations[k]
                comps = func["components"]
                # Hard-lock filter check on combination
                cand_score = self.calculate_substitution_score(
                    orig_node=k,
                    cand_node=" + ".join(comps),
                    context=context,
                    user_diet=dietary_preference,
                    user_allergens=user_allergens,
                )
                if cand_score > 0:
                    has_components = all(c in pantry_set for c in comps)
                    candidates.append({
                        "substitute": " + ".join(comps),
                        "is_functional_combo": True,
                        "substitution_type": "combination",
                        "components": comps,
                        "in_pantry": has_components,
                        "ratio": func["ratio"],
                        "confidence": "high",
                        "score": (cand_score + 10.0) if has_components else cand_score,
                        "reason": func["reason"],
                    })

        # 2. Query Graph Edges for all lookup keys
        matched_node = None
        for k in lookup_keys:
            if self.graph.has_node(k):
                matched_node = k
                for u, v, data in self.graph.out_edges(k, data=True):
                    score = self.calculate_substitution_score(
                        orig_node=u,
                        cand_node=v,
                        context=context,
                        user_diet=dietary_preference,
                        user_allergens=user_allergens,
                    )
                    if score > 0:
                        candidates.append({
                            "substitute": v,
                            "is_functional_combo": False,
                            "substitution_type": data.get("substitution_type", "direct"),
                            "components": [v],
                            "in_pantry": v in pantry_set,
                            "ratio": data.get("ratio", "1:1"),
                            "confidence": data.get("confidence", "high"),
                            "score": score + (10.0 if v in pantry_set else 0.0),
                            "reason": data.get("reason", "Provides equivalent culinary properties."),
                        })

        if not matched_node and not candidates:
            logger.debug(f"[Graph] Missing node in graph for {missing_ingredient} (canonical: {canonical})")
            from backend.app.substitutions.taxonomy import match_culinary_taxonomy
            tax_class = match_culinary_taxonomy(missing_ingredient) or match_culinary_taxonomy(canonical)
            if tax_class:
                for default_sub in tax_class.default_substitutes:
                    sub_name = default_sub["substitute"]
                    user_algs_clean = [a.lower().strip() for a in (user_allergens or [])]
                    entry_algs = [a.strip() for a in default_sub["allergens"].split(",") if a.strip()]
                    if any(a in user_algs_clean for a in entry_algs):
                        continue
                    diet_str = (dietary_preference or "").lower().strip()
                    cand_diets = [d.strip() for d in default_sub["dietary"].split(",") if d.strip()]
                    if diet_str and diet_str not in cand_diets and "vegan" not in cand_diets:
                        continue
                    score = 65.0 + (10.0 if any(c.strip() in pantry_set for c in sub_name.split(" or ")) else 0.0)
                    candidates.append({
                        "substitute": sub_name,
                        "is_functional_combo": False,
                        "substitution_type": default_sub["type"],
                        "components": [sub_name],
                        "in_pantry": any(c.strip() in pantry_set for c in sub_name.split(" or ")),
                        "ratio": default_sub["ratio"],
                        "confidence": default_sub["confidence"],
                        "score": score,
                        "reason": default_sub["reason"],
                    })

        # Sort candidates by score
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return {
            "missing_ingredient": missing_ingredient,
            "canonical": canonical,
            "candidates": candidates[:3],
        }


substitution_graph = IngredientSubstitutionGraph()
