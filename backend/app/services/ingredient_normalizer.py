"""
backend/app/services/ingredient_normalizer.py

Ingredient Normalization Service:
Maps recognized raw ingredient labels, regional terms, and visual detection strings
to the canonical ingredient names used by the SQLite index and recipe dataset.
"""

import re
from typing import Dict, List, Optional, Tuple


# Known domain synonyms and regional term mappings
SYNONYM_MAP: Dict[str, str] = {
    # Dairy & Indian kitchen staples
    "dahi": "curd",
    "yoghurt": "curd",
    "yogurt": "curd",
    "plain yogurt": "curd",
    "greek yogurt": "curd",
    "cottage cheese": "paneer",
    "indian cottage cheese": "paneer",
    "fresh paneer": "paneer",
    "cream": "heavy cream",
    "malai": "heavy cream",
    "ghee": "clarified butter",
    "cow milk": "milk",
    "whole milk": "milk",
    
    # Vegetables & Produce
    "bell pepper": "capsicum",
    "green bell pepper": "capsicum",
    "red bell pepper": "capsicum",
    "yellow bell pepper": "capsicum",
    "sweet pepper": "capsicum",
    "green capsicum": "capsicum",
    "red capsicum": "capsicum",
    "yellow capsicum": "capsicum",
    "aubergine": "eggplant",
    "brinjal": "eggplant",
    "courgette": "zucchini",
    "cilantro": "coriander",
    "fresh cilantro": "coriander",
    "fresh coriander": "coriander",
    "coriander leaves": "coriander",
    "green chili": "green chilli",
    "green chillies": "green chilli",
    "green chili pepper": "green chilli",
    "chilli": "green chilli",
    "chili": "green chilli",
    "red onion": "onion",
    "white onion": "onion",
    "yellow onion": "onion",
    "diced onion": "onion",
    "spring onion": "scallion",
    "green onion": "scallion",
    "scallions": "scallion",
    "sweet corn": "corn",
    "maize": "corn",
    "diced tomato": "tomato",
    "diced tomatoes": "tomato",
    "chopped tomato": "tomato",
    "chopped tomatoes": "tomato",
    "chopped onion": "onion",
    "chopped onions": "onion",
    "chopped potato": "potato",
    "chopped potatoes": "potato",
    "diced potato": "potato",
    "diced potatoes": "potato",
    "ginger root": "ginger",
    "fresh ginger": "ginger",
    "garlic cloves": "garlic",
    "fresh garlic": "garlic",
    
    # Grains, Pulses & Legumes
    "basmati rice": "rice",
    "white rice": "rice",
    "brown rice": "rice",
    "raw rice": "rice",
    "atta": "wheat flour",
    "gehu atta": "wheat flour",
    "flour": "wheat flour",
    "all purpose flour": "flour",
    "maida": "flour",
    "rolled oats": "oats",
    "dal": "lentils",
    "daal": "lentils",
    "yellow moong dal": "lentils",
    "moong dal": "lentils",
    "split moong dal": "lentils",
    "toor dal": "lentils",
    "arhar dal": "lentils",
    "chana dal": "lentils",
    "urad dal": "lentils",
    "red lentils": "masoor dal",
    "yellow lentils": "lentils",
    "chana": "chickpeas",
    "garbanzo": "chickpeas",
    "garbanzo beans": "chickpeas",
    "rajma": "kidney beans",
    "chawal": "rice",
    "turmeric powder": "turmeric",
    "haldi": "turmeric",
    
    # Common pantry items
    "egg": "eggs",
    "hen egg": "eggs",
    "cooking oil": "vegetable oil",
    "sunflower oil": "vegetable oil",
    "mustard oil": "oil",
}

# Supported canonical ingredient dictionary (aligned with corpus)
CANONICAL_INGREDIENTS = {
    "tomato", "onion", "potato", "carrot", "capsicum", "cucumber", "cabbage",
    "cauliflower", "spinach", "garlic", "ginger", "green chilli", "eggplant",
    "zucchini", "peas", "corn", "mushroom", "lemon", "lime", "apple", "banana",
    "orange", "mango", "curd", "paneer", "milk", "butter", "cheese", "heavy cream",
    "rice", "wheat flour", "flour", "oats", "lentils", "chickpeas", "kidney beans",
    "eggs", "bread", "coriander", "olive oil", "vegetable oil", "mustard", "cumin",
    "turmeric", "black pepper", "salt", "sugar", "soy sauce", "pasta"
}


class IngredientNormalizer:
    """
    Normalizes free-form ingredient text and computer vision predictions
    into clean canonical database entities.
    """

    def clean_text(self, text: str) -> str:
        """Lowercases, trims, and removes noisy special characters."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def to_singular(self, word: str) -> str:
        """Basic English lemmatization for common food plurals."""
        # Special cases
        if word.endswith("tomatoes"):
            return word[:-2]  # tomato
        if word.endswith("potatoes"):
            return word[:-2]  # potato
        if word.endswith("chillies"):
            return word[:-3] + "y"  # chilli
        if word.endswith("berries"):
            return word[:-3] + "y"
        if word.endswith("leaves"):
            return word[:-3] + "f"
        if word.endswith("ies") and len(word) > 4:
            return word[:-3] + "y"
        if word.endswith("es") and len(word) > 4 and word[-3] in "sxcxz":
            return word[:-2]
        if word.endswith("s") and not word.endswith("ss") and not word in {"rice", "oats", "chickpeas", "lentils", "eggs"}:
            return word[:-1]
        return word

    def normalize(self, raw_name: str) -> Tuple[str, float, bool]:
        """
        Normalizes an ingredient name.
        Returns:
            canonical_name (str): The resolved canonical name.
            mapping_confidence (float): Confidence of the mapping (0.0 to 1.0).
            is_resolved (bool): True if mapped to a known canonical category.
        """
        cleaned = self.clean_text(raw_name)
        if not cleaned:
            return "unknown", 0.0, False

        # 1. Exact canonical match
        if cleaned in CANONICAL_INGREDIENTS:
            return cleaned, 1.0, True

        # 2. Known synonym dictionary lookup
        if cleaned in SYNONYM_MAP:
            return SYNONYM_MAP[cleaned], 0.98, True

        # 3. Singularization match
        singular = self.to_singular(cleaned)
        if singular in CANONICAL_INGREDIENTS:
            return singular, 0.95, True
        if singular in SYNONYM_MAP:
            return SYNONYM_MAP[singular], 0.95, True

        # 4. Multi-word prefix/suffix extraction (e.g. "fresh ripe tomato" -> "tomato")
        for canonical in CANONICAL_INGREDIENTS:
            # Word boundary search
            pattern = rf"\b{re.escape(canonical)}\b"
            if re.search(pattern, cleaned):
                return canonical, 0.90, True

        for syn_key, target in SYNONYM_MAP.items():
            pattern = rf"\b{re.escape(syn_key)}\b"
            if re.search(pattern, cleaned):
                return target, 0.88, True

        # 5. Token-level overlap (fuzzy fallback)
        cleaned_tokens = set(cleaned.split())
        best_match = None
        best_score = 0.0

        for canonical in CANONICAL_INGREDIENTS:
            c_tokens = set(canonical.split())
            intersection = cleaned_tokens.intersection(c_tokens)
            if intersection:
                score = len(intersection) / max(len(cleaned_tokens), len(c_tokens))
                if score > best_score and score >= 0.5:
                    best_score = score
                    best_match = canonical

        if best_match and best_score >= 0.6:
            return best_match, round(best_score * 0.85, 2), True

        # Unresolved
        return cleaned, 0.40, False


ingredient_normalizer = IngredientNormalizer()
