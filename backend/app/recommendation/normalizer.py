import re
from typing import List, Set, Tuple

# Words ending in 's' that are singular and must not have trailing 's' removed
PROTECTED_SINGULARS: Set[str] = {
    "asparagus",
    "molasses",
    "hummus",
    "couscous",
    "citrus",
    "watercress",
    "lemongrass",
    "swiss cheese",
    "feta cheese",
    "parmesan cheese",
    "ricotta cheese",
    "goat cheese",
    "blue cheese",
    "cream cheese",
    "cheddar cheese",
    "provolone cheese",
    "mozzarella cheese",
    "monterey jack cheese",
    "cottage cheese",
    "gouda cheese",
    "brie cheese",
    "havarti cheese",
    "fontina cheese",
    "asiago cheese",
    "gruyere cheese",
    "manchego cheese",
    "colby cheese",
    "colby jack cheese",
    "curry leaves",
    "bay leaves",
    "brussels sprouts",
    "oats",
    "rolled oats",
    "quick oats",
    "groats",
    "chia seeds",
    "sesame seeds",
    "flax seeds",
    "poppy seeds",
    "sunflower seeds",
    "pumpkin seeds",
    "mustard seeds",
    "caraway seeds",
    "fennel seeds",
    "coriander seeds",
    "cumin seeds",
    "dill seeds",
    "anise seeds",
    "celery seeds",
}

QUANTITY_PREFIX_RE = re.compile(
    r"^(?:(?:\d+\s+\d+/\d+|\d+/\d+|\d+\s*-\s*\d+|\d+(?:\.\d+)?)\s*|"
    r"(?:one|two|three|four|five|six|seven|eight|nine|ten|half|quarter|a|an|some|few|several)\s+)",
    re.IGNORECASE,
)

COMMON_UNITS: Set[str] = {
    "cup", "cups", "c.", "tbsp", "tablespoon", "tablespoons", "tbs", "tbsps",
    "tsp", "teaspoon", "teaspoons", "oz", "ounce", "ounces", "fl oz", "fl. oz.",
    "lb", "lbs", "pound", "pounds", "g", "gram", "grams", "kg", "kilo", "kilogram", "kilograms",
    "ml", "milliliter", "milliliters", "l", "liter", "liters", "clove", "cloves",
    "can", "cans", "tin", "tins", "package", "packages", "pkg", "pkgs",
    "bunch", "bunches", "head", "heads", "stalk", "stalks", "slice", "slices",
    "piece", "pieces", "pcs", "pinch", "pinches", "dash", "dashes", "handful",
    "handfuls", "sprig", "sprigs", "stick", "sticks", "bottle", "bottles",
    "jar", "jars", "box", "boxes", "bag", "bags",
}

COMMON_MODIFIERS: Set[str] = {
    "fresh", "freshly", "diced", "chopped", "minced", "sliced", "peeled",
    "unpeeled", "cooked", "uncooked", "raw", "frozen", "canned", "organic",
    "whole", "crushed", "grated", "shredded", "mashed", "roasted", "baked",
    "boiled", "fried", "warm", "cold", "hot", "sweet", "large", "medium",
    "small", "extra-large", "lean", "boneless", "skinless", "ripe", "coarse",
    "fine", "ground", "russet", "red", "white", "yellow", "yukon", "gold", "baby",
}

SIZE_MODIFIERS: Set[str] = {
    "large", "medium", "small", "extra-large", "extra large", "med", "lg", "sm",
}

CULINARY_SYNONYMS: Dict[str, Set[str]] = {
    "scallion": {"scallion", "scallions", "green onion", "green onions", "spring onion", "spring onions"},
    "green onion": {"scallion", "scallions", "green onion", "green onions", "spring onion", "spring onions"},
    "cilantro": {"cilantro", "coriander", "fresh coriander", "coriander leaves"},
    "coriander": {"cilantro", "coriander", "fresh coriander", "coriander leaves"},
    "aubergine": {"aubergine", "aubergines", "eggplant", "eggplants"},
    "eggplant": {"aubergine", "aubergines", "eggplant", "eggplants"},
    "courgette": {"courgette", "courgettes", "zucchini", "zucchinis"},
    "zucchini": {"courgette", "courgettes", "zucchini", "zucchinis"},
    "bell pepper": {"bell pepper", "bell peppers", "sweet pepper", "sweet peppers", "capsicum"},
    "capsicum": {"bell pepper", "bell peppers", "sweet pepper", "sweet peppers", "capsicum"},
    "chickpea": {"chickpea", "chickpeas", "garbanzo bean", "garbanzo beans", "garbanzo"},
    "garbanzo": {"chickpea", "chickpeas", "garbanzo bean", "garbanzo beans", "garbanzo"},
    "potato": {"potato", "potatoes", "russet potato", "russet potatoes", "baking potato", "idaho potato", "yukon gold potato", "all-purpose potato"},
    "potatoes": {"potato", "potatoes", "russet potato", "russet potatoes", "baking potato", "idaho potato", "yukon gold potato", "all-purpose potato"},
    "russet potato": {"potato", "potatoes", "russet potato", "russet potatoes"},
    "russet potatoes": {"potato", "potatoes", "russet potato", "russet potatoes"},
}


def extract_core_food(text: str) -> str:
    """
    Semantically extracts the core food concept from raw ingredient text by stripping
    quantities (e.g. '4', 'two', '1/2'), units (e.g. 'cups', 'cloves', 'lbs'),
    connectives ('of'), preparation clauses after commas, and harmless prep adjectives ('diced', 'large', 'medium', 'peeled').
    E.g. '4 potatoes' -> 'potatoes'
         '4 medium potatoes, peeled and cut into 1/2-inch strips' -> 'potatoes'
         '2 large russet potatoes' -> 'potatoes'
         '3 cups of diced onions' -> 'onions'
         'medium potatoes' -> 'potatoes'
         'potatoes' -> 'potatoes'
    """
    if not text:
        return ""

    t = text.lower().strip()
    # Strip harmless surrounding punctuation
    t = t.strip("\"'.,;:#?!*~`()[]{}")

    # If ingredient contains comma or semicolon (e.g. '4 medium potatoes, peeled and cut...'),
    # extract the primary ingredient part before the preparation instruction
    if "," in t:
        t = t.split(",")[0].strip()
    if ";" in t:
        t = t.split(";")[0].strip()

    t = " ".join(t.split())

    # 1. Strip leading quantity prefix (e.g. '4 ', 'two ', '1/2 ')
    t = QUANTITY_PREFIX_RE.sub("", t).strip()

    # 2. Check for units and connective 'of'
    words = t.split()
    if words and words[0] in COMMON_UNITS:
        words = words[1:]
    if words and words[0] == "of":
        words = words[1:]

    # 3. Strip leading modifier adjectives (e.g. 'medium', 'large', 'peeled', etc.)
    while len(words) > 1 and words[0] in COMMON_MODIFIERS:
        words = words[1:]

    # Also handle trailing count/quantity e.g. 'potatoes 4' or 'potatoes, 4'
    if words and re.match(r"^\d+$", words[-1]):
        words = words[:-1]

    core = " ".join(words).strip()
    return core if core else t


def normalize_pantry_ingredient(ingredient: str) -> str:
    """
    Normalizes a single pantry ingredient:
    - Lowercase, trim, strip punctuation
    - Strips quantities and units (e.g. '4 potatoes' -> 'potatoes', '2 cups flour' -> 'flour')
    - Strips size/prep modifiers when modifying a food noun (e.g. 'medium potatoes' -> 'potatoes', '4 medium potatoes' -> 'potatoes')
    - Preserves descriptive multi-word ingredients (e.g. 'fresh tomatoes', 'garlic powder')
    """
    if not ingredient:
        return ""
    cleaned = ingredient_clean(ingredient)
    if "," in cleaned:
        cleaned = cleaned.split(",")[0].strip()
    if ";" in cleaned:
        cleaned = cleaned.split(";")[0].strip()

    # Strip leading quantity prefix (e.g. '4 ', '2 ')
    cleaned = QUANTITY_PREFIX_RE.sub("", cleaned).strip()
    words = cleaned.split()
    if words and words[0] in COMMON_UNITS:
        words = words[1:]
    if words and words[0] == "of":
        words = words[1:]

    # Strip leading size modifiers when more words follow (e.g. 'medium potatoes' -> 'potatoes')
    # while preserving descriptive descriptors (e.g. 'fresh tomatoes', 'garlic powder')
    while len(words) > 1 and words[0] in SIZE_MODIFIERS:
        words = words[1:]

    cleaned = " ".join(words).strip()
    # Strip trailing numbers (e.g. 'potatoes 4')
    cleaned = re.sub(r"\s+\d+$", "", cleaned).strip()
    return cleaned if cleaned else ingredient_clean(ingredient)


def is_same_food(a: str, b: str) -> bool:
    """
    Determines if two food representations semantically represent the same food.
    e.g. is_same_food('potatoes', 'medium potatoes') -> True
         is_same_food('4 medium potatoes', 'potatoes') -> True
         is_same_food('potatoes', 'potato') -> True
    """
    if not a or not b:
        return False
    a_clean = ingredient_clean(a)
    b_clean = ingredient_clean(b)
    if a_clean == b_clean:
        return True

    core_a = extract_core_food(a)
    core_b = extract_core_food(b)
    if core_a and core_b:
        if core_a == core_b:
            return True
        sing_a = to_singular_form(core_a)
        sing_b = to_singular_form(core_b)
        if sing_a == sing_b:
            return True
        if sing_a in CULINARY_SYNONYMS and sing_b in CULINARY_SYNONYMS[sing_a]:
            return True
        if sing_b in CULINARY_SYNONYMS and sing_a in CULINARY_SYNONYMS[sing_b]:
            return True

    return False


def to_singular_form(term: str) -> str:
    """
    Safely converts a regular plural food noun to its singular form.
    Only operates on the final word if term is multi-word (e.g. 'fresh tomatoes' -> 'fresh tomato').
    Guards protected singulars (e.g. 'asparagus', 'couscous').
    """
    cleaned = ingredient_clean(term)
    if not cleaned or cleaned in PROTECTED_SINGULARS:
        return cleaned

    words = cleaned.split(" ")
    last_word = words[-1]

    # If the last word is protected, do not de-pluralize
    if last_word in PROTECTED_SINGULARS:
        return cleaned

    singular_last = last_word

    # Rule 1: -ies -> -y (e.g. cherries -> cherry, strawberries -> strawberry)
    # Exclude very short words like 'pies' -> 'pie', 'ties' -> 'tie'
    if last_word.endswith("ies") and len(last_word) > 4:
        singular_last = last_word[:-3] + "y"
    # Rule 2: -es after s, x, z, ch, sh, o (e.g. tomatoes -> tomato, potatoes -> potato)
    elif last_word.endswith("es"):
        if re.search(r"(s|x|z|ch|sh|o)es$", last_word):
            if last_word in ("tomatoes", "potatoes"):
                singular_last = last_word[:-2]
            elif re.search(r"(ch|sh|ss|x|z)es$", last_word):
                singular_last = last_word[:-2]
            else:
                singular_last = last_word[:-1]
        else:
            singular_last = last_word[:-1]
    # Rule 3: Regular -s (e.g. onions -> onion, eggs -> egg, carrots -> carrot)
    elif last_word.endswith("s") and not last_word.endswith("ss") and len(last_word) > 2:
        singular_last = last_word[:-1]

    if singular_last != last_word:
        words[-1] = singular_last
        return " ".join(words)

    return cleaned


def to_plural_form(term: str) -> str:
    """
    Safely derives the standard plural form of a food noun for index lookup.
    """
    cleaned = ingredient_clean(term)
    if not cleaned or cleaned in PROTECTED_SINGULARS:
        return cleaned

    words = cleaned.split(" ")
    last_word = words[-1]

    if last_word in PROTECTED_SINGULARS:
        return cleaned

    # Already plural checks
    if last_word in ("potatoes", "tomatoes"):
        return cleaned
    if last_word in ("potato", "tomato"):
        plural_last = last_word + "es"
    elif last_word.endswith("ies"):
        return cleaned
    elif last_word.endswith("y") and not re.search(r"[aeiou]y$", last_word) and len(last_word) > 2:
        plural_last = last_word[:-1] + "ies"
    elif last_word.endswith("es"):
        return cleaned
    elif re.search(r"(s|x|z|ch|sh)$", last_word):
        plural_last = last_word + "es"
    elif not last_word.endswith("s"):
        plural_last = last_word + "s"
    else:
        plural_last = last_word

    words[-1] = plural_last
    return " ".join(words)


def ingredient_clean(term: str) -> str:
    """Basic string cleanup without quantity removal."""
    if not term:
        return ""
    cleaned = term.lower().strip()
    cleaned = " ".join(cleaned.split())
    cleaned = cleaned.strip("\"'.,;:#?!*~`()[]{}")
    return cleaned


def get_lookup_variants(term: str) -> Set[str]:
    """
    Given a user pantry term (e.g. '4 potatoes', 'potatoes', or 'fresh tomato'),
    returns the comprehensive set of safe lookup variants:
    - Core singular and plural forms (e.g. 'potato', 'potatoes')
    - Exact cleaned form and its singular/plural
    - Known culinary synonyms
    """
    cleaned = ingredient_clean(term)
    if not cleaned:
        return set()

    variants = {cleaned}
    singular_raw = to_singular_form(cleaned)
    plural_raw = to_plural_form(cleaned)
    variants.add(singular_raw)
    variants.add(plural_raw)

    # Core food extraction
    core = extract_core_food(cleaned)
    if core:
        variants.add(core)
        core_singular = to_singular_form(core)
        core_plural = to_plural_form(core)
        variants.add(core_singular)
        variants.add(core_plural)

        # Check synonyms
        if core in CULINARY_SYNONYMS:
            variants.update(CULINARY_SYNONYMS[core])
        if core_singular in CULINARY_SYNONYMS:
            variants.update(CULINARY_SYNONYMS[core_singular])

    return {v for v in variants if v}


def normalize_pantry_list(ingredients: List[str]) -> Tuple[List[str], Set[str]]:
    """
    Normalizes a list of pantry ingredients provided by the user.
    Semantically deduplicates entries: '4 potatoes' and 'potatoes' will be
    identified as the exact same ingredient and deduplicated.
    Returns:
    - deduplicated list of canonical normalized pantry ingredients
    - comprehensive set of safe lookup variants for all items
    """
    normalized_list = []
    seen_cores = set()
    all_lookup_variants = set()

    for item in ingredients:
        canonical = normalize_pantry_ingredient(item)
        if not canonical:
            continue

        core = extract_core_food(canonical)
        core_key = to_singular_form(core) if core else canonical

        if core_key not in seen_cores:
            seen_cores.add(core_key)
            normalized_list.append(canonical)

        # Collect all lookup variants for this ingredient
        variants = get_lookup_variants(item)
        variants.update(get_lookup_variants(canonical))
        all_lookup_variants.update(variants)

    return normalized_list, all_lookup_variants

