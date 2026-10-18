"""
backend/app/substitutions/taxonomy.py

Scalable Culinary Role Taxonomy & Dynamic Functional Substitutions.
Enables universal missing-ingredient coverage for newly encountered ingredients
without hardcoding individual logic for every variant.
"""

import re
from typing import Dict, List, Optional, Tuple
from backend.app.substitutions.models import SubstitutionEntry

class CulinaryTaxonomyClass:
    def __init__(
        self,
        category: str,
        keywords: List[str],
        default_substitutes: List[Dict[str, str]],
        structural: bool = False,
        optional_omission: bool = False,
    ):
        self.category = category
        self.keywords = keywords
        self.default_substitutes = default_substitutes
        self.structural = structural
        self.optional_omission = optional_omission
        self.pattern = re.compile(r"\b(" + "|".join(re.escape(k) for k in keywords) + r")\b", re.IGNORECASE)

CULINARY_TAXONOMY: List[CulinaryTaxonomyClass] = [
    # 1. Cooking Oils & Liquid Fats
    CulinaryTaxonomyClass(
        category="cooking_oil",
        keywords=[
            "oil", "olive oil", "vegetable oil", "canola oil", "sunflower oil", "corn oil",
            "grapeseed oil", "peanut oil", "safflower oil", "avocado oil", "sesame oil",
            "coconut oil", "cooking spray", "shortening", "lard"
        ],
        default_substitutes=[
            {
                "substitute": "vegetable oil or olive oil",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Neutral or mild cooking oils provide equivalent culinary fat, heat transfer, and moisture binding.",
                "notes": "Select vegetable or canola oil for high-heat frying, or olive oil for savory sautéing.",
                "use_cases": "frying,cooking,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            },
            {
                "substitute": "melted butter or margarine",
                "ratio": "1:1",
                "confidence": "medium",
                "reason": "Melted butter or plant margarine provides equivalent fat moisture and richness in skillet sautéing and batters.",
                "notes": "Butter has a lower smoke point; sauté over medium heat.",
                "use_cases": "baking,frying,cooking",
                "dietary": "vegetarian",
                "allergens": "dairy",
                "type": "functional"
            }
        ],
        structural=False,
    ),

    # 2. Vinegars & Food Acids
    CulinaryTaxonomyClass(
        category="vinegar_acid",
        keywords=[
            "vinegar", "cider vinegar", "apple cider vinegar", "white vinegar", "red wine vinegar",
            "white wine vinegar", "balsamic vinegar", "rice vinegar", "malt vinegar", "tarragon vinegar",
            "lemon juice", "lime juice"
        ],
        default_substitutes=[
            {
                "substitute": "apple cider vinegar or lemon juice",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Mild food acids provide equivalent brightness, acidity, and chemical reaction with leaveners.",
                "notes": "Use 1:1 ratio for deglazing, dressings, or marinades.",
                "use_cases": "sauces,salads,cooking,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            },
            {
                "substitute": "white vinegar diluted with a pinch of sugar",
                "ratio": "1:1",
                "confidence": "medium",
                "reason": "Recreates balanced culinary acidity without overpowering the dish.",
                "notes": "Best for savory dressings and sauces.",
                "use_cases": "sauces,salads,cooking",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            }
        ],
        structural=False,
    ),

    # 3. Flours & Starches (Structural)
    CulinaryTaxonomyClass(
        category="flour_starch",
        keywords=[
            "flour", "all-purpose flour", "bread flour", "cake flour", "pastry flour", "self-rising flour",
            "whole wheat flour", "oat flour", "rye flour", "spelt flour", "almond flour", "cornstarch",
            "potato starch", "tapioca starch", "arrowroot", "rice flour"
        ],
        default_substitutes=[
            {
                "substitute": "all-purpose flour or 1:1 gluten-free baking blend",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Provides essential starch granules and matrix structure for baking and pan-thickening.",
                "notes": "Whisk thoroughly to prevent clumping in batters or slurries.",
                "use_cases": "baking,sauces,cooking,general",
                "dietary": "vegetarian,vegan",
                "allergens": "gluten",
                "type": "functional"
            },
            {
                "substitute": "cornstarch (for thickening sauces)",
                "ratio": "1:0.5 (2 tbsp flour = 1 tbsp cornstarch)",
                "confidence": "high",
                "reason": "Cornstarch has double the thickening power of grain flour with a clean finish.",
                "notes": "Dissolve in cold liquid before stirring into hot simmering liquids.",
                "use_cases": "sauces,cooking",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            }
        ],
        structural=True,
    ),

    # 4. Milks & Plant Milks
    CulinaryTaxonomyClass(
        category="milk_liquid",
        keywords=[
            "milk", "whole milk", "skim milk", "lowfat milk", "evaporated milk", "condensed milk",
            "buttermilk", "soy milk", "almond milk", "oat milk", "coconut milk", "cashew milk",
            "rice milk", "half and half", "heavy cream", "light cream", "whipping cream"
        ],
        default_substitutes=[
            {
                "substitute": "oat milk or soy milk (unsweetened)",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Provides comparable liquid hydration, protein-to-fat balance, and neutral mouthfeel in batters and sauces.",
                "notes": "Select plain unsweetened variety for savory cooking.",
                "use_cases": "baking,sauces,cooking,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            },
            {
                "substitute": "whole milk",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Standard dairy milk delivering balanced moisture, natural sugars, and creamy body.",
                "notes": "Universal 1:1 substitute in all standard baking and stovetop recipes.",
                "use_cases": "baking,sauces,cooking,general",
                "dietary": "vegetarian",
                "allergens": "dairy",
                "type": "direct"
            }
        ],
        structural=False,
    ),

    # 5. Sweeteners & Sugars
    CulinaryTaxonomyClass(
        category="sweetener",
        keywords=[
            "sugar", "white sugar", "granulated sugar", "brown sugar", "dark brown sugar", "light brown sugar",
            "cane sugar", "powdered sugar", "confectioners sugar", "icing sugar", "honey", "maple syrup",
            "agave nectar", "molasses", "corn syrup", "golden syrup", "turbinado sugar", "coconut sugar"
        ],
        default_substitutes=[
            {
                "substitute": "white granulated sugar or brown sugar",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Standard culinary sugars deliver identical sucrose sweetness, hygroscopic moisture retention, and browning.",
                "notes": "Brown sugar adds a deeper caramel note and tender crumb.",
                "use_cases": "baking,dessert,sauces,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            },
            {
                "substitute": "pure maple syrup or agave nectar",
                "ratio": "1:0.75",
                "confidence": "medium",
                "reason": "Natural liquid sweeteners providing clean sweetness and dissolved moisture.",
                "notes": "Reduce recipe liquid slightly if replacing dry granulated sugar.",
                "use_cases": "baking,cooking,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            }
        ],
        structural=True,
    ),

    # 6. Broths, Stocks & Bouillons
    CulinaryTaxonomyClass(
        category="broth_stock",
        keywords=[
            "broth", "stock", "chicken broth", "chicken stock", "beef broth", "beef stock",
            "vegetable broth", "vegetable stock", "bouillon", "bone broth", "turkey broth",
            "fish stock", "clam juice", "dashi"
        ],
        default_substitutes=[
            {
                "substitute": "vegetable broth or vegetable bouillon",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Mirepoix-simmered vegetable stock provides savory umami foundation and moisture in soups, sauces, and braises.",
                "notes": "Universally compatible across all dietary preferences.",
                "use_cases": "sauces,cooking,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            },
            {
                "substitute": "water seasoned with butter or olive oil and herbs",
                "ratio": "1:1 (1 cup water + 1 tbsp butter/oil + pinch herbs)",
                "confidence": "medium",
                "reason": "Provides liquid volume, cooking fat, and aromatic finish when pre-made broth is not on hand.",
                "notes": "Season with a pinch of salt and black pepper.",
                "use_cases": "sauces,cooking",
                "dietary": "vegetarian",
                "allergens": "",
                "type": "functional"
            }
        ],
        structural=False,
    ),

    # 7. Cheeses
    CulinaryTaxonomyClass(
        category="cheese",
        keywords=[
            "cheese", "cheddar", "cheddar cheese", "parmesan", "parmesan cheese", "mozzarella",
            "mozzarella cheese", "swiss cheese", "provolone", "gouda", "monterey jack", "feta",
            "feta cheese", "ricotta", "cottage cheese", "cream cheese", "goat cheese", "blue cheese",
            "gruyere", "fontina", "pecorino", "romano"
        ],
        default_substitutes=[
            {
                "substitute": "monterey jack or mild cheddar cheese",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Semi-firm melting cheeses provide equivalent creamy fat, smooth melt, and savory dairy richness.",
                "notes": "Grate or shred fresh from the block for superior melting.",
                "use_cases": "baking,sauces,cooking,general",
                "dietary": "vegetarian",
                "allergens": "dairy",
                "type": "functional"
            },
            {
                "substitute": "plant-based vegan cheese shreds or nutritional yeast",
                "ratio": "1:1",
                "confidence": "medium",
                "reason": "Plant-based alternatives deliver savory umami and gooey melted layers without dairy.",
                "notes": "Nutritional yeast is ideal for dusting over pasta; vegan shreds for melting.",
                "use_cases": "baking,sauces,salads,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            }
        ],
        structural=False,
    ),

    # 8. Alliums (Onions, Garlic, Shallots, Leeks)
    CulinaryTaxonomyClass(
        category="allium",
        keywords=[
            "onion", "yellow onion", "white onion", "red onion", "sweet onion", "shallot",
            "shallots", "scallion", "scallions", "green onion", "green onions", "leek", "leeks",
            "garlic", "clove garlic", "garlic cloves", "chives"
        ],
        default_substitutes=[
            {
                "substitute": "yellow onion or shallots (diced)",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Alliums share natural sulfurous sweetness and aromatic foundation essential for savory mirepoix sautéing.",
                "notes": "Sauté gently in butter or oil until translucent.",
                "use_cases": "frying,cooking,sauces,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            },
            {
                "substitute": "onion powder or garlic powder",
                "ratio": "1 medium onion = 1 tbsp powder; 1 clove garlic = 1/8 tsp powder",
                "confidence": "medium",
                "reason": "Dehydrated ground alliums supply pure flavor compounds evenly throughout sauces and skillet mixtures.",
                "notes": "Dissolves seamlessly without changing texture.",
                "use_cases": "sauces,cooking,frying,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            }
        ],
        structural=False,
    ),

    # 9. Mushrooms & Fungi
    CulinaryTaxonomyClass(
        category="mushroom_fungi",
        keywords=[
            "mushroom", "mushrooms", "cremini", "portobello", "portabello", "shiitake", "button mushroom",
            "white mushroom", "chanterelle", "porcini", "oyster mushroom"
        ],
        default_substitutes=[
            {
                "substitute": "cremini or white button mushrooms",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Cultivated mushrooms provide matching earthy umami, moisture release, and tender chew in skillet sautés and sauces.",
                "notes": "Brown in skillet with fat without overcrowding pan.",
                "use_cases": "frying,sauces,cooking,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            },
            {
                "substitute": "diced zucchini or eggplant",
                "ratio": "1:1",
                "confidence": "medium",
                "reason": "Absorbs savory skillet aromatics and provides matching tender volume and moisture in pasta sauces.",
                "notes": "Add a splash of soy sauce or nutritional yeast for savory depth.",
                "use_cases": "frying,sauces,cooking",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            }
        ],
        structural=False,
    ),

    # 10. Bell Peppers & Capsicums
    CulinaryTaxonomyClass(
        category="capsicum",
        keywords=[
            "bell pepper", "green pepper", "green bell pepper", "red pepper", "red bell pepper",
            "yellow pepper", "yellow bell pepper", "poblano", "capsicum", "sweet pepper"
        ],
        default_substitutes=[
            {
                "substitute": "red or yellow bell pepper",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Sweet bell peppers provide identical crisp texture, aromatic moisture, and structural bulk.",
                "notes": "Slightly sweeter profile that complements skillet dishes and sautés.",
                "use_cases": "frying,salads,sauces,cooking,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            },
            {
                "substitute": "sliced celery or diced zucchini",
                "ratio": "1:1",
                "confidence": "medium",
                "reason": "Celery supplies aromatic crunch and moisture in vegetable bases; zucchini provides tender volume.",
                "notes": "Dice finely and sauté alongside onions.",
                "use_cases": "frying,sauces,cooking",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            }
        ],
        structural=False,
    ),

    # 11. Ground & Cured Meats
    CulinaryTaxonomyClass(
        category="meat_poultry",
        keywords=[
            "ground beef", "ground pork", "ground turkey", "ground chicken", "beef", "chicken",
            "pork", "turkey", "hamburger", "bacon", "sausage", "pepperoni", "salami", "ham"
        ],
        default_substitutes=[
            {
                "substitute": "ground turkey or ground chicken",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Browns into comparable crumbled protein texture and savory richness in skillet dishes and casseroles.",
                "notes": "Add 1 tbsp olive oil if using lean poultry to preserve moisture.",
                "use_cases": "frying,sauces,baking,cooking,general",
                "dietary": "non_vegetarian",
                "allergens": "",
                "type": "functional"
            },
            {
                "substitute": "cooked brown lentils or crumbled firm tofu",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Plant proteins absorb savory aromatics and provide identical crumbled bulk and mouthfeel.",
                "notes": "Simmer in sauce for 15 minutes to absorb flavors.",
                "use_cases": "frying,sauces,cooking,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            }
        ],
        structural=True,
    ),

    # 12. Fresh Herbs & Garnishes (Safe Optional Omission)
    CulinaryTaxonomyClass(
        category="herbal_garnish",
        keywords=[
            "parsley", "fresh parsley", "flat leaf parsley", "cilantro", "fresh cilantro",
            "chives", "basil", "fresh basil", "mint", "fresh mint", "dill", "fresh dill",
            "tarragon", "rosemary", "thyme", "oregano", "sesame seeds"
        ],
        default_substitutes=[
            {
                "substitute": "dried herb equivalent (e.g. 1 tsp dried for 1 tbsp fresh)",
                "ratio": "1:0.33",
                "confidence": "medium",
                "reason": "Concentrated dried herbs provide essential herbal aroma and earthy depth.",
                "notes": "Add earlier in cooking to allow herbs to rehydrate and bloom.",
                "use_cases": "cooking,sauces,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            }
        ],
        structural=False,
        optional_omission=True,
    ),

    # 13. Common Legumes & Beans
    CulinaryTaxonomyClass(
        category="legume_beans",
        keywords=[
            "black beans", "kidney beans", "pinto beans", "cannellini beans", "chickpeas",
            "garbanzo beans", "navy beans", "great northern beans", "lentils", "black-eyed peas"
        ],
        default_substitutes=[
            {
                "substitute": "pinto beans, black beans, or cannellini beans",
                "ratio": "1:1",
                "confidence": "high",
                "reason": "Canned or cooked legumes share comparable starch density, creamy mouthfeel, and fiber bulk.",
                "notes": "Rinse and drain canned beans before adding to dish.",
                "use_cases": "cooking,sauces,salads,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            }
        ],
        structural=False,
    ),

    # 14. Citrus Fruits & Zest
    CulinaryTaxonomyClass(
        category="citrus",
        keywords=[
            "lemon", "lime", "orange", "grapefruit", "lemon zest", "lime zest", "orange zest"
        ],
        default_substitutes=[
            {
                "substitute": "bottled lemon or lime juice",
                "ratio": "1:1 (or 1/2 tsp zest = 1 tsp juice)",
                "confidence": "high",
                "reason": "Delivers equivalent citric acid brightness and aromatic top notes.",
                "notes": "Add at the end of cooking for fresh brightness.",
                "use_cases": "salads,sauces,cooking,baking,general",
                "dietary": "vegetarian,vegan",
                "allergens": "",
                "type": "functional"
            }
        ],
        structural=False,
    ),
]


def match_culinary_taxonomy(ingredient_name: str) -> Optional[CulinaryTaxonomyClass]:
    """
    Identifies the culinary category of a newly encountered ingredient
    by checking normalized token patterns against the universal taxonomy.
    """
    if not ingredient_name:
        return None
    clean = ingredient_name.lower().strip()
    for tax_class in CULINARY_TAXONOMY:
        if tax_class.pattern.search(clean):
            return tax_class
    return None
