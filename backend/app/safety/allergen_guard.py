"""
backend/app/safety/allergen_guard.py

Novelty 2: Cross-Contamination + Hard-Lock Allergen Safety Layer
Dual-layer safety model:
Layer A: Deterministic & Semantic Hard-Lock Allergen & Dietary Database (Blocks violations BEFORE ranking).
Layer B: Contextual RAG Audit (Audits recipe instructions for hidden risks & cross-contact language).
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel

from backend.app.recommendation.normalizer import (
    to_singular_form,
    to_plural_form,
    extract_core_food,
    CULINARY_SYNONYMS,
)

class SafetyCheckResult(BaseModel):
    recipe_id: int
    recipe_title: str
    status: str  # "SAFE", "CAUTION", "BLOCKED"
    is_blocked: bool
    reasons: List[str]
    warnings: List[str]
    allergens_detected: List[str]
    contextual_risks: List[str]


# Comprehensive allergen taxonomy covering FDA Big 9 + major global allergens and common sensitivities
ALLERGEN_TAXONOMY: Dict[str, List[str]] = {
    "gluten": [
        "flour", "wheat", "barley", "rye", "pasta", "bread", "breadcrumbs",
        "soy sauce", "seitan", "semolina", "couscous", "spelt", "malt", "malt extract",
        "farina", "graham", "kamut"
    ],
    "wheat": [
        "wheat", "flour", "breadcrumbs", "pasta", "semolina", "couscous", "spelt"
    ],
    "dairy": [
        "milk", "butter", "cream", "cheese", "yogurt", "sour cream", "buttermilk",
        "whey", "ghee", "parmesan", "cheddar", "mozzarella", "ricotta", "paneer",
        "casein", "caseinate", "curd", "mascarpone", "provolone", "gouda", "brie",
        "heavy cream", "whipping cream", "condensed milk", "evaporated milk"
    ],
    "milk": [
        "milk", "butter", "cream", "cheese", "yogurt", "sour cream", "buttermilk",
        "whey", "ghee", "casein", "parmesan", "cheddar", "mozzarella"
    ],
    "peanuts": [
        "peanut", "peanuts", "peanut butter", "peanut oil", "groundnut", "groundnuts",
        "arachis oil"
    ],
    "peanut": [
        "peanut", "peanuts", "peanut butter", "peanut oil", "groundnut", "groundnuts"
    ],
    "tree_nuts": [
        "almond", "walnut", "cashew", "pecan", "pistachio", "macadamia", "hazelnut",
        "almonds", "walnuts", "cashews", "pecans", "pistachios", "hazelnuts",
        "brazil nut", "brazil nuts", "chestnut", "chestnuts", "pine nut", "pine nuts",
        "marzipan", "praline", "nougat"
    ],
    "tree nuts": [
        "almond", "walnut", "cashew", "pecan", "pistachio", "macadamia", "hazelnut",
        "almonds", "walnuts", "cashews", "pecans", "pistachios", "hazelnuts",
        "pine nut", "pine nuts"
    ],
    "nuts": [
        "peanut", "peanuts", "almond", "walnut", "cashew", "pecan", "pistachio",
        "macadamia", "hazelnut", "almonds", "walnuts", "cashews", "pine nut"
    ],
    "eggs": [
        "egg", "eggs", "mayonnaise", "eggnog", "egg whites", "egg yolks",
        "meringue", "albumin", "ovalbumin", "lysozyme"
    ],
    "egg": [
        "egg", "eggs", "mayonnaise", "eggnog", "egg whites", "egg yolks", "meringue"
    ],
    "soy": [
        "soy", "soya", "tofu", "tempeh", "edamame", "soy sauce", "soy milk",
        "tamari", "miso", "natto", "soybean", "soybeans", "textured vegetable protein"
    ],
    "fish": [
        "fish", "salmon", "tuna", "cod", "anchovy", "anchovies", "fish sauce",
        "worcestershire", "trout", "halibut", "sardine", "sardines", "tilapia",
        "mackerel", "bass", "snapper", "flounder", "haddock", "swordfish"
    ],
    "shellfish": [
        "shrimp", "shrimps", "prawn", "prawns", "crab", "crabs", "lobster", "lobsters",
        "clam", "clams", "mussel", "mussels", "oyster", "oysters", "squid", "calamari",
        "octopus", "scallop", "scallops", "crawfish", "crayfish"
    ],
    "shrimp": [
        "shrimp", "shrimps", "prawn", "prawns"
    ],
    "sesame": [
        "sesame", "tahini", "sesame oil", "sesame seeds", "sesamol"
    ],
    "mustard": [
        "mustard", "mustard seed", "mustard seeds", "dijon", "dijon mustard"
    ],
    "pork": [
        "pork", "bacon", "ham", "prosciutto", "pancetta", "pork chop", "pork chops",
        "lard", "pork sausage", "pork ribs", "pork loin", "chorizo", "pepperoni"
    ],
    "beef": [
        "beef", "steak", "ground beef", "veal", "sirloin", "ribeye", "roast beef",
        "beef broth", "corned beef"
    ],
    "potatoes": [
        "potato", "potatoes", "russet potato", "baking potato", "mashed potato",
        "mashed potatoes", "french fries", "hash browns", "potato starch", "potato flour"
    ],
    "potato": [
        "potato", "potatoes", "russet potato", "baking potato", "mashed potato",
        "mashed potatoes", "french fries", "hash browns", "potato starch", "potato flour"
    ],
    "mushrooms": [
        "mushroom", "mushrooms", "cremini", "shiitake", "portobello", "button mushroom",
        "porcini", "chanterelle"
    ],
    "mushroom": [
        "mushroom", "mushrooms", "cremini", "shiitake", "portobello", "button mushroom"
    ],
    "strawberries": [
        "strawberry", "strawberries"
    ],
    "strawberry": [
        "strawberry", "strawberries"
    ],
    "nightshades": [
        "tomato", "tomatoes", "potato", "potatoes", "eggplant", "eggplants",
        "bell pepper", "chili", "chili pepper", "cayenne", "paprika"
    ],
}

CROSS_CONTACT_TERMS: List[str] = [
    "may contain", "processed in a facility", "manufactured on shared equipment",
    "traces of", "cross-contamination", "cross-contact", "shared fryer"
]


def expand_user_allergen_semantically(allergen: str) -> Set[str]:
    """
    Expands any arbitrary user allergen into a set of prohibited keywords and variants:
    1. Checks predefined taxonomy for category-level expansion (e.g. 'dairy' -> milk, cheese, butter...).
    2. Derives core food concept, singular, plural, and synonyms (e.g. '4 potatoes' -> 'potato', 'potatoes').
    3. Handles natural language phrases like 'allergic to shrimp' or 'exclude dairy'.
    """
    raw = allergen.lower().strip()
    # Strip common conversational prefixes
    clean = re.sub(r"^(?:exclude|allergic\s+to|allergy\s+to|no)\s+", "", raw).strip()
    clean = clean.strip("\"'.,;:#?!*~`()[]{}")
    if not clean:
        return set()

    prohibited_keywords: Set[str] = set()

    # 1. Check exact or underscore-normalized taxonomy
    tax_key = clean.replace(" ", "_")
    if clean in ALLERGEN_TAXONOMY:
        prohibited_keywords.update(ALLERGEN_TAXONOMY[clean])
    elif tax_key in ALLERGEN_TAXONOMY:
        prohibited_keywords.update(ALLERGEN_TAXONOMY[tax_key])

    # 2. Extract core food noun
    core = extract_core_food(clean)
    if core in ALLERGEN_TAXONOMY:
        prohibited_keywords.update(ALLERGEN_TAXONOMY[core])
    elif core.replace(" ", "_") in ALLERGEN_TAXONOMY:
        prohibited_keywords.update(ALLERGEN_TAXONOMY[core.replace(" ", "_")])

    # 3. Add singular and plural forms of clean and core
    sing_clean = to_singular_form(clean)
    plur_clean = to_plural_form(clean)
    sing_core = to_singular_form(core) if core else ""
    plur_core = to_plural_form(core) if core else ""

    for term in (clean, core, sing_clean, plur_clean, sing_core, plur_core):
        if term and len(term) > 1:
            prohibited_keywords.add(term)

    # 4. Check culinary synonyms
    for term in (clean, core, sing_clean, sing_core):
        if term in CULINARY_SYNONYMS:
            prohibited_keywords.update(CULINARY_SYNONYMS[term])

    # Reverse lookup in taxonomy values (e.g. user typed 'almond' -> finds tree_nuts family)
    for cat_name, items in ALLERGEN_TAXONOMY.items():
        if clean in items or core in items or sing_core in items:
            prohibited_keywords.update(items)

    return {k for k in prohibited_keywords if k}


def check_term_in_text_with_word_boundaries(term: str, text: str) -> bool:
    """
    Checks if a term appears as a distinct word in text using word boundaries.
    Prevents false positives like 'egg' matching 'eggplant' or 'ham' matching 'graham'.
    """
    if not term or not text:
        return False
    # If term has spaces, check regex phrase
    pattern = rf"\b{re.escape(term)}(?:s|es)?\b"
    return bool(re.search(pattern, text, re.IGNORECASE))


class AllergenGuard:
    """
    Dual-layer Allergen Guard enforcing hard safety locks and instruction audits.
    Supports arbitrary custom user allergens analyzed semantically.
    """

    def check_recipe_safety(
        self,
        recipe_id: int,
        recipe_title: str,
        ingredients: List[str],
        directions: List[str],
        user_allergens: Optional[List[str]] = None,
        user_diet: Optional[str] = None,
        recipe_ner: Optional[List[str]] = None,
    ) -> SafetyCheckResult:
        user_allergens = [a.strip() for a in (user_allergens or []) if a and a.strip()]
        user_diet = (user_diet or "").lower().strip()

        reasons = []
        warnings = []
        allergens_detected = []
        contextual_risks = []

        all_ingredients_str = " \n ".join([i.lower() for i in ingredients])
        all_directions_str = " \n ".join([d.lower() for d in directions])
        clean_title = (recipe_title or "").lower()
        ner_tokens = [n.lower().strip() for n in (recipe_ner or [])]

        # Layer A: Semantic Hard-Lock Allergen Check
        is_blocked = False
        for allergen in user_allergens:
            prohibited_terms = expand_user_allergen_semantically(allergen)
            matched_term = None

            # 1. Check against structured NER tokens if available
            for term in prohibited_terms:
                sing_term = to_singular_form(term)
                for ner in ner_tokens:
                    if ner == term or to_singular_form(ner) == sing_term or extract_core_food(ner) == term:
                        matched_term = ner
                        break
                if matched_term:
                    break

            # 2. Check against full ingredient text with word-boundary precision
            if not matched_term:
                for term in prohibited_terms:
                    if check_term_in_text_with_word_boundaries(term, all_ingredients_str):
                        matched_term = term
                        break

            # 3. Check against recipe title
            if not matched_term:
                for term in prohibited_terms:
                    if check_term_in_text_with_word_boundaries(term, clean_title):
                        matched_term = term
                        break

            if matched_term:
                is_blocked = True
                allergens_detected.append(allergen)
                reasons.append(
                    f"Contains prohibited allergen '{allergen}' (detected ingredient: '{matched_term}' in recipe)."
                )

        # Check Hard Diet Restrictions
        norm_diet = user_diet.lower().strip()
        if norm_diet in ("vegetarian", "veg", "vegetarian_compatible"):
            meat_keywords = [
                "chicken", "beef", "pork", "lamb", "bacon", "salmon", "shrimp",
                "fish", "turkey", "pork chop", "pork chops", "veal", "duck", "prosciutto",
                "sausage", "pepperoni", "gelatin", "tuna", "anchovy", "anchovies",
                "crab", "lobster", "clam", "mussel", "oyster", "squid", "calamari",
                "octopus", "scallop", "prawn", "prawns", "ham", "steak", "meatball",
                "meatballs", "lard", "chorizo", "salami", "pancetta", "ribs", "brisket",
                "poultry", "meat", "ground beef", "roast beef", "sirloin", "tenderloin",
                "venison", "bison", "goat", "mutton", "meatloaf", "halibut", "cod",
                "tilapia", "trout", "sardine", "sardines"
            ]
            for m in meat_keywords:
                if (check_term_in_text_with_word_boundaries(m, all_ingredients_str) or 
                    check_term_in_text_with_word_boundaries(m, clean_title) or
                    any(m == n or m in n.split() for n in ner_tokens)):
                    is_blocked = True
                    reasons.append(f"Violates Vegetarian preference (contains '{m}').")
                    break
        elif norm_diet in ("vegan", "vegan_compatible"):
            non_vegan = [
                "chicken", "beef", "pork", "lamb", "salmon", "shrimp", "fish",
                "turkey", "bacon", "tuna", "ham", "sausage", "pepperoni", "prawn",
                "crab", "lobster", "milk", "butter", "cheese", "egg", "eggs",
                "honey", "cream", "yogurt", "paneer", "whey", "casein", "gelatin",
                "lard", "ghee", "prosciutto", "meatball", "meatballs"
            ]
            for nv in non_vegan:
                if (check_term_in_text_with_word_boundaries(nv, all_ingredients_str) or 
                    check_term_in_text_with_word_boundaries(nv, clean_title) or
                    any(nv == n or nv in n.split() for n in ner_tokens)):
                    is_blocked = True
                    reasons.append(f"Violates Vegan preference (contains '{nv}').")
                    break

        if is_blocked:
            return SafetyCheckResult(
                recipe_id=recipe_id,
                recipe_title=recipe_title,
                status="BLOCKED",
                is_blocked=True,
                reasons=reasons,
                warnings=warnings,
                allergens_detected=list(set(allergens_detected)),
                contextual_risks=contextual_risks,
            )

        # Layer B: Contextual RAG Instruction Audit for Hidden Risks & Cross-Contact
        for term in CROSS_CONTACT_TERMS:
            if term in all_directions_str:
                contextual_risks.append(f"Cross-contact warning in directions: '{term}'")
                warnings.append(f"Instruction text contains caution phrasing ('{term}').")

        # Hidden sauce / derivative checks
        hidden_risk_map = {
            "worcestershire": "Worcestershire sauce may contain hidden anchovies (fish allergen).",
            "curry paste": "Commercial curry paste may contain hidden shrimp paste or fish sauce.",
            "caesar": "Caesar dressing traditionally contains anchovies and raw egg yolk."
        }
        for term, note in hidden_risk_map.items():
            if term in all_ingredients_str or term in all_directions_str:
                contextual_risks.append(note)
                warnings.append(note)

        status = "CAUTION" if (warnings or contextual_risks) else "SAFE"

        return SafetyCheckResult(
            recipe_id=recipe_id,
            recipe_title=recipe_title,
            status=status,
            is_blocked=False,
            reasons=reasons,
            warnings=warnings,
            allergens_detected=list(set(allergens_detected)),
            contextual_risks=contextual_risks,
        )

allergen_guard = AllergenGuard()

