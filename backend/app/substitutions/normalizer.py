"""
backend/app/substitutions/normalizer.py

Ingredient normalization pipeline for the Smart Substitution Graph.
Strips culinary preparation descriptors, package modifiers, and quantity prefixes
while mapping common aliases to canonical ingredient keys without losing original text.
"""

import re
from typing import Dict, List, Optional, Set, Tuple

# Common preparation and state descriptors to strip from missing ingredient tokens
PREPARATION_DESCRIPTORS: List[str] = [
    r"\bchopped\b",
    r"\bsliced\b",
    r"\bdiced\b",
    r"\bminced\b",
    r"\bshredded\b",
    r"\bgrated\b",
    r"\bcrushed\b",
    r"\bpeeled\b",
    r"\bseeded\b",
    r"\bdrained\b",
    r"\bmelted\b",
    r"\bcooked\b",
    r"\braw\b",
    r"\bfresh\b",
    r"\bfreshly\b",
    r"\bdried\b",
    r"\bdry\b",
    r"\bfrozen\b",
    r"\bthawed\b",
    r"\broasted\b",
    r"\btoasted\b",
    r"\bbaked\b",
    r"\bboiled\b",
    r"\bsteamed\b",
    r"\bfinely\b",
    r"\bcoarsely\b",
    r"\bthinly\b",
    r"\broughly\b",
    r"\bsoftened\b",
    r"\bwarmed\b",
    r"\bchilled\b",
    r"\bcanned\b",
    r"\bwhole\b",
    r"\bhalved\b",
    r"\bquartered\b",
    r"\bshelled\b",
    r"\bboneless\b",
    r"\bskinless\b",
    r"\bunsalted\b",
    r"\bsalted\b",
    r"\blean\b",
    r"\bground\b",
    r"\bshaved\b",
    r"\bcrumbled\b",
    r"\blarge\b",
    r"\bsmall\b",
    r"\bmedium\b",
    r"\blg\b",
    r"\bsm\b",
    r"\bmed\b",
]

DESCRIPTOR_REGEX = re.compile("|".join(PREPARATION_DESCRIPTORS), re.IGNORECASE)

# Mapping of common recipe aliases and brand/type variations to canonical ingredient names
INGREDIENT_ALIASES: Dict[str, str] = {
    # Mushrooms
    "portabello mushrooms": "mushroom",
    "portabello mushroom": "mushroom",
    "portabella mushrooms": "mushroom",
    "portabella mushroom": "mushroom",
    "portobello mushrooms": "mushroom",
    "portobello mushroom": "mushroom",
    "cremini mushrooms": "mushroom",
    "cremini mushroom": "mushroom",
    "baby bella mushrooms": "mushroom",
    "baby bella mushroom": "mushroom",
    "white button mushrooms": "mushroom",
    "button mushrooms": "mushroom",
    "button mushroom": "mushroom",
    "sliced mushrooms": "mushroom",
    "wild mushrooms": "mushroom",
    "shiitake mushrooms": "mushroom",
    "shiitake mushroom": "mushroom",
    "mushrooms": "mushroom",
    
    # Peppers
    "green bell pepper": "green bell pepper",
    "green bell peppers": "green bell pepper",
    "green pepper": "green bell pepper",
    "green peppers": "green bell pepper",
    "red bell pepper": "red bell pepper",
    "red bell peppers": "red bell pepper",
    "red pepper": "red bell pepper",
    "red peppers": "red bell pepper",
    "yellow bell pepper": "bell pepper",
    "yellow pepper": "bell pepper",
    "bell pepper": "bell pepper",
    "bell peppers": "bell pepper",
    "sweet pepper": "bell pepper",
    "sweet peppers": "bell pepper",
    "capsicum": "bell pepper",
    
    # Meats & Sausages
    "pepperoni": "pepperoni",
    "pepperonis": "pepperoni",
    "sliced pepperoni": "pepperoni",
    "turkey pepperoni": "pepperoni",
    "italian sausage": "italian sausage",
    "sweet italian sausage": "italian sausage",
    "ground beef": "ground beef",
    "ground pork": "ground pork",
    "ground turkey": "ground turkey",
    "bacon": "bacon",
    "bacon strips": "bacon",
    "pancetta": "bacon",
    "prosciutto": "prosciutto",
    "ham": "ham",
    
    # Cheeses
    "mozzarella cheese": "mozzarella",
    "mozzarella": "mozzarella",
    "fresh mozzarella": "mozzarella",
    "part skim mozzarella": "mozzarella",
    "shredded mozzarella": "mozzarella",
    "parmesan cheese": "parmesan",
    "parmesan": "parmesan",
    "parmigiano reggiano": "parmesan",
    "pecorino": "parmesan",
    "cheddar cheese": "cheddar cheese",
    "cheddar": "cheddar cheese",
    "sharp cheddar": "cheddar cheese",
    "monterey jack": "monterey jack cheese",
    "jack cheese": "monterey jack cheese",
    "provolone cheese": "provolone cheese",
    "provolone": "provolone cheese",
    "ricotta cheese": "ricotta cheese",
    "ricotta": "ricotta cheese",
    "cottage cheese": "cottage cheese",
    "feta cheese": "feta cheese",
    "feta": "feta cheese",
    
    # Alliums
    "yellow onion": "onion",
    "white onion": "onion",
    "red onion": "onion",
    "sweet onion": "onion",
    "spanish onion": "onion",
    "onions": "onion",
    "green onions": "green onion",
    "green onion": "green onion",
    "scallions": "green onion",
    "scallion": "green onion",
    "shallots": "shallot",
    "shallot": "shallot",
    "garlic cloves": "garlic",
    "garlic clove": "garlic",
    "cloves garlic": "garlic",
    
    # Dairy & Liquids
    "whole milk": "milk",
    "skim milk": "milk",
    "2% milk": "milk",
    "heavy whipping cream": "heavy cream",
    "whipping cream": "heavy cream",
    "double cream": "heavy cream",
    "greek yogurt": "plain greek yogurt",
    "yogurt": "plain greek yogurt",
    
    # Herbs & Seasonings
    "fresh basil": "basil",
    "dried basil": "basil",
    "fresh parsley": "parsley",
    "dried parsley": "parsley",
    "fresh cilantro": "cilantro",
    "coriander leaves": "cilantro",
    "fresh oregano": "oregano",
    "dried oregano": "oregano",
    
    # Pantry Staples
    "extra virgin olive oil": "olive oil",
    "pure olive oil": "olive oil",
    "canola": "canola oil",
    "vegetable cooking oil": "vegetable oil",
    "all purpose flour": "all-purpose flour",
    "ap flour": "all-purpose flour",
    "plain flour": "all-purpose flour",
    "white flour": "all-purpose flour",
    "granulated sugar": "white sugar",
    "table sugar": "white sugar",
    "confectioners sugar": "powdered sugar",
    "icing sugar": "powdered sugar",
    "light brown sugar": "brown sugar",
    "dark brown sugar": "brown sugar",
    
    # Fruits
    "ripe bananas": "banana",
    "ripe banana": "banana",
    "bananas": "banana",
}


def normalize_ingredient_token(raw_name: str) -> str:
    """
    Cleans, strips preparation descriptors and punctuation from an ingredient token.
    Returns the cleaned lowercase stem.
    """
    if not raw_name:
        return ""

    text = raw_name.lower().strip()

    # Remove quantity numbers and fractions (e.g. '1/2', '2 to 3', '20 oz', '1 lb')
    text = re.sub(r"^\s*(\d+/\d+|\d+(\.\d+)?|\d+\s*to\s*\d+)\s*", "", text)
    # Remove package sizes in parentheses: '(20 ounce)', '(3 oz.)'
    text = re.sub(r"\(.*?\)", "", text)
    # Remove units (c., cup, cups, oz, lb, lbs, can, pkg, tbsp, tsp, clove, cloves)
    unit_pattern = r"\b(cup|cups|c\.|c|oz|ounce|ounces|lb|lbs|pound|pounds|pkg|package|can|jar|tbsp|tablespoon|tablespoons|tsp|teaspoon|teaspoons|clove|cloves|bottle|bunch|pinch|dash)\b"
    text = re.sub(unit_pattern, "", text, flags=re.IGNORECASE)

    # Strip descriptors
    text = DESCRIPTOR_REGEX.sub("", text)

    # Normalize punctuation and extra spaces
    text = re.sub(r"[^\w\s-]", " ", text)
    text = " ".join(text.split()).strip()

    return text


def resolve_canonical_ingredient(raw_name: str) -> str:
    """
    Resolves any raw ingredient string to its canonical graph/database key.
    Applies descriptor cleaning, alias lookup, and singularization.
    """
    cleaned = normalize_ingredient_token(raw_name)
    if not cleaned:
        cleaned = raw_name.lower().strip()

    # 1. Direct alias match
    if cleaned in INGREDIENT_ALIASES:
        return INGREDIENT_ALIASES[cleaned]

    # 2. Check raw string directly against aliases (in case descriptors weren't stripped)
    raw_lower = raw_name.lower().strip()
    if raw_lower in INGREDIENT_ALIASES:
        return INGREDIENT_ALIASES[raw_lower]

    # 3. Trailing 's' de-pluralization check against aliases
    if cleaned.endswith("s") and cleaned[:-1] in INGREDIENT_ALIASES:
        return INGREDIENT_ALIASES[cleaned[:-1]]

    # 4. Check for compound words (e.g. "sliced portabello mushrooms" contains "mushroom")
    for alias_key, canonical in INGREDIENT_ALIASES.items():
        if alias_key in cleaned or cleaned in alias_key:
            return canonical

    # 5. Fall back to singular or cleaned string
    if cleaned.endswith("s") and len(cleaned) > 3 and not cleaned.endswith("ss"):
        return cleaned[:-1]

    return cleaned
