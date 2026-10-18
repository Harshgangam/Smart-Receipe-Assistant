from typing import Dict, List, Set, Tuple

# Supported Cuisines Taxonomy
SUPPORTED_CUISINES: List[str] = [
    "American",
    "Asian",
    "Chinese",
    "Dessert",
    "French",
    "Indian",
    "Italian",
    "Japanese",
    "Korean",
    "Mediterranean",
    "Mexican",
    "Middle Eastern",
    "Soup",
    "Thai",
]


# Cuisine Title Keywords: High-confidence evidence when appearing in recipe titles
CUISINE_TITLE_KEYWORDS: Dict[str, List[str]] = {
    "Italian": [
        "italian", "pizza", "pasta", "spaghetti", "lasagna", "lasagne",
        "risotto", "parmesan", "pesto", "carbonara", "bolognese", "fettuccine",
        "gnocchi", "ravioli", "calzone", "bruschetta", "tiramisu", "cannoli",
        "margherita", "marinara", "alfredo", "manicotti", "tortellini", "frittata",
    ],
    "Mexican": [
        "mexican", "taco", "tacos", "enchilada", "enchiladas", "salsa",
        "guacamole", "fajita", "fajitas", "quesadilla", "quesadillas",
        "burrito", "burritos", "chimichanga", "tamale", "tamales",
        "pico de gallo", "carnitas", "chile verde", "chile relleno",
    ],
    "Indian": [
        "indian", "curry", "masala", "tikka", "tandoori", "samosa", "samosas",
        "paneer", "naan", "biryani", "dal", "daal", "dhal", "korma", "vindaloo",
        "rogan josh", "chana", "raita", "chutney", "pakora", "pakoras",
    ],
    "Chinese": [
        "chinese", "stir fry", "stir-fry", "chow mein", "lo mein", "wonton",
        "wontons", "kung pao", "szechuan", "sichuan", "potsticker", "potstickers",
        "dumpling", "dumplings", "fried rice", "egg roll", "egg rolls",
        "sweet and sour", "moo shu", "general tso", "orange chicken",
    ],
    "Japanese": [
        "japanese", "teriyaki", "sushi", "miso", "ramen", "tempura", "udon",
        "soba", "edamame", "yakitori", "katsu", "sashimi", "gyoza", "donburi",
    ],
    "Thai": [
        "thai", "pad thai", "tom yum", "tom kha", "green curry", "red curry",
        "panang", "massaman", "satay", "drunken noodles", "pad see ew",
    ],
    "Korean": [
        "korean", "kimchi", "bulgogi", "bibimbap", "gochujang", "japchae",
        "galbi", "kalbi", "tteokbokki", "korean bbq", "samgyeopsal",
    ],
    "Mediterranean": [
        "mediterranean", "greek", "tzatziki", "falafel", "hummus", "tabbouleh",
        "moussaka", "souvlaki", "gyro", "gyros", "spanakopita", "dolma", "baklava",
    ],
    "Middle Eastern": [
        "middle eastern", "shawarma", "tahini", "baba ghanoush", "shakshuka",
        "fattoush", "kofta", "kebabs", "kebab", "kabob", "kabobs",
    ],
    "French": [
        "french", "quiche", "crepe", "crepes", "fondue", "ratatouille",
        "croissant", "croissants", "souffle", "coq au vin", "bourguignon",
        "hollandaise", "bechamel", "provencal", "au gratin",
    ],
    "American": [
        "american", "burger", "burgers", "cheeseburger", "cheeseburgers",
        "barbecue", "bbq", "cornbread", "pot roast", "buffalo wings",
        "sloppy joe", "sloppy joes", "meatloaf", "coleslaw", "clam chowder",
    ],
}

# Signature Co-Occurring Ingredient Profiles: Medium-confidence evidence
CUISINE_INGREDIENT_PROFILES: Dict[str, List[Set[str]]] = {
    "Indian": [
        {"garam masala"},
        {"curry powder", "turmeric"},
        {"cumin", "coriander", "turmeric"},
        {"ghee", "cumin", "ginger"},
        {"paneer"},
        {"cardamom", "cumin", "turmeric"},
    ],
    "Italian": [
        {"basil", "oregano", "parmesan"},
        {"pasta", "oregano", "garlic", "olive oil"},
        {"ricotta", "mozzarella", "parmesan"},
        {"spaghetti", "tomato sauce"},
        {"pesto", "pine nuts"},
    ],
    "Mexican": [
        {"tortillas", "salsa"},
        {"tortilla", "cheddar cheese", "salsa"},
        {"taco seasoning"},
        {"enchilada sauce"},
        {"jalapeno", "cilantro", "lime", "cumin"},
        {"black beans", "salsa", "cumin"},
    ],
    "Chinese": [
        {"soy sauce", "sesame oil", "ginger"},
        {"soy sauce", "hoisin sauce"},
        {"oyster sauce", "soy sauce"},
        {"five spice powder"},
        {"wonton wrappers"},
        {"water chestnuts", "soy sauce", "ginger"},
    ],
    "Japanese": [
        {"mirin", "soy sauce"},
        {"miso paste"},
        {"sake", "soy sauce", "mirin"},
        {"dashi"},
        {"nori", "sushi rice"},
        {"wasabi"},
    ],
    "Thai": [
        {"fish sauce", "coconut milk"},
        {"curry paste", "coconut milk"},
        {"lemongrass", "fish sauce"},
        {"thai basil"},
        {"galangal"},
    ],
    "Korean": [
        {"gochujang"},
        {"kimchi"},
        {"gochugaru"},
        {"sesame oil", "soy sauce", "garlic", "scallions"},
    ],
    "Mediterranean": [
        {"feta cheese", "kalamata olives"},
        {"feta", "olive oil", "oregano"},
        {"tahini", "lemon juice", "garlic"},
        {"tzatziki"},
    ],
    "Middle Eastern": [
        {"sumac"},
        {"za'atar"},
        {"pomegranate molasses"},
        {"cardamom", "tahini"},
    ],
    "French": [
        {"dijon mustard", "white wine", "butter"},
        {"tarragon", "shallots", "white wine"},
        {"herbes de provence"},
        {"gruyere cheese", "white wine"},
    ],
    "American": [
        {"bbq sauce", "brown sugar"},
        {"cheddar cheese", "bacon", "ranch dressing"},
        {"hot pepper sauce", "butter"},  # buffalo style
        {"yellow mustard", "relish", "ketchup"},
    ],
}

# Obvious Non-Vegetarian Exclusions (Meat, Poultry, Seafood, Animal By-Products)
NON_VEGETARIAN_EXCLUSIONS: Set[str] = {
    # Red Meat & Game
    "beef", "ground beef", "lean ground beef", "stew beef", "beef broth",
    "beef bouillon", "beef stock", "steak", "sirloin", "flank steak",
    "ribeye", "pork", "ground pork", "pork chops", "pork loin", "pork roast",
    "pork tenderloin", "bacon", "thick-cut bacon", "canadian bacon", "pancetta",
    "ham", "cooked ham", "diced ham", "prosciutto", "sausage", "italian sausage",
    "pork sausage", "breakfast sausage", "chorizo", "pepperoni", "salami",
    "hot dogs", "hot dog", "frankfurters", "lamb", "ground lamb", "lamb chops",
    "veal", "venison", "meatballs", "meatball", "meatloaf",

    # Poultry
    "chicken", "chicken breasts", "boneless chicken breasts", "chicken breast",
    "chicken thighs", "chicken wings", "chicken tenders", "cooked chicken",
    "shredded chicken", "ground chicken", "chicken broth", "chicken stock",
    "chicken bouillon", "cream of chicken soup", "turkey", "ground turkey",
    "turkey breast", "duck", "pheasant",

    # Seafood & Fish
    "fish", "fish fillets", "salmon", "salmon fillets", "canned salmon",
    "tuna", "canned tuna", "albacore tuna", "cod", "tilapia", "halibut",
    "trout", "catfish", "anchovies", "anchovy", "sardines", "sardine",
    "shrimp", "medium shrimp", "large shrimp", "prawns", "crab", "crabmeat",
    "imitation crabmeat", "lobster", "scallops", "clams", "canned clams",
    "mussels", "oysters", "squid", "calamari", "octopus", "seafood",
    "fish sauce", "oyster sauce", "clam juice", "worcestershire sauce",

    # Animal By-products
    "gelatin", "unflavored gelatin", "lard", "shortening (lard)",
}

# Non-Vegan Animal Derivatives (Dairy, Eggs, Honey)
ANIMAL_DERIVED_EXCLUSIONS: Set[str] = {
    # Dairy
    "milk", "whole milk", "skim milk", "low-fat milk", "evaporated milk",
    "condensed milk", "sweetened condensed milk", "buttermilk", "heavy cream",
    "whipping cream", "heavy whipping cream", "sour cream", "light sour cream",
    "half and half", "half-and-half", "ice cream", "butter", "unsalted butter",
    "melted butter", "ghee",

    # Cheeses
    "cheese", "cheddar cheese", "shredded cheddar cheese", "mozzarella cheese",
    "shredded mozzarella cheese", "parmesan cheese", "grated parmesan cheese",
    "cream cheese", "ricotta cheese", "cottage cheese", "feta cheese",
    "swiss cheese", "provolone cheese", "monterey jack cheese", "pepper jack cheese",
    "colby cheese", "gouda cheese", "blue cheese", "goat cheese", "brie cheese",
    "sharp cheddar cheese", "mild cheddar cheese", "velveeta cheese",

    # Eggs
    "egg", "eggs", "large egg", "large eggs", "egg whites", "egg yolks",
    "egg white", "egg yolk", "hard-boiled eggs", "mayonnaise",

    # Bee & Other products
    "honey", "pure honey", "raw honey", "whey", "casein",
}
