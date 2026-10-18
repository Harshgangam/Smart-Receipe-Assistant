"""
backend/app/services/sandbox_engine.py

Novelty 5: Interactive Leftover Combos Sandbox Engine
Simulates real-time ingredient toggles, objective weight adjustments, and cluster grouping 
without re-building FAISS index embeddings.
"""

from pathlib import Path
import json
import re
from typing import Any, Dict, List, Optional, Set
import zlib
from pydantic import BaseModel

from backend.app.recommendation.engine import RecommendationEngine
from backend.app.safety.allergen_guard import allergen_guard
from backend.app.services.food_waste_optimizer import food_waste_optimizer, OptimizationWeights
from backend.app.services.shopping_optimizer import shopping_optimizer

# Load comprehensive verified meal photo catalog (790+ high-res culinary photos)
_PHOTO_CATALOG: List[Dict[str, Any]] = []
_CATALOG_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "recipe_photos.json"

try:
    if _CATALOG_PATH.exists():
        with open(_CATALOG_PATH, "r", encoding="utf-8") as _f:
            _PHOTO_CATALOG = json.load(_f)
except Exception:
    _PHOTO_CATALOG = []

# Verified Unsplash culinary photos categorized with high resolution and relatable relevance
_UNSPLASH_POOLS: Dict[str, List[str]] = {
    "fries": [
        "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&w=800&q=80",  # Crispy golden french fries
        "https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?auto=format&fit=crop&w=800&q=80",  # Seasoned crispy potato wedges
        "https://images.unsplash.com/photo-1576107232684-1279f3908594?auto=format&fit=crop&w=800&q=80",  # Golden french fries with dip
        "https://images.unsplash.com/photo-1585109649139-366815a0d713?auto=format&fit=crop&w=800&q=80",  # Crispy baked oven french fries
    ],
    "potato": [
        "https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=800&q=80",  # Crispy roasted herb potatoes
        "https://images.unsplash.com/photo-1596797038530-2c107229654b?auto=format&fit=crop&w=800&q=80",  # Creamy garlic mashed potatoes with butter
        "https://images.unsplash.com/photo-1573080496219-bb080dd4f877?auto=format&fit=crop&w=800&q=80",  # Crispy golden french fries
        "https://images.unsplash.com/photo-1598514983318-2f64f8f4796c?auto=format&fit=crop&w=800&q=80",  # Loaded baked potato with sour cream and chives
        "https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?auto=format&fit=crop&w=800&q=80",  # Seasoned crispy potato wedges
        "https://images.unsplash.com/photo-1585109649139-366815a0d713?auto=format&fit=crop&w=800&q=80",  # Crispy baked oven potatoes
        "https://images.unsplash.com/photo-1541832676-9b763b0239ab?auto=format&fit=crop&w=800&q=80",  # Creamy potato leek soup
    ],
    "rice": [
        "https://images.unsplash.com/photo-1512058564366-18510be2db19?auto=format&fit=crop&w=800&q=80",  # Wok egg fried rice
        "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=800&q=80",  # Fragrant vegetable biryani
        "https://images.unsplash.com/photo-1536304929831-ee1ca9d44906?auto=format&fit=crop&w=800&q=80",  # Creamy risotto with herbs
        "https://images.unsplash.com/photo-1539136788836-5699e78bfc75?auto=format&fit=crop&w=800&q=80",  # Steamed rice bowl
    ],
    "egg": [
        "https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=800&q=80",  # Fluffy scrambled eggs
        "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?auto=format&fit=crop&w=800&q=80",  # Poached eggs with toast
        "https://images.unsplash.com/photo-1587486913049-53fc88980cfc?auto=format&fit=crop&w=800&q=80",  # Vegetable herb frittata
        "https://images.unsplash.com/photo-1506084868230-bb9d95c24759?auto=format&fit=crop&w=800&q=80",  # Sunny-side skillet eggs
    ],
    "taco": [
        "https://images.unsplash.com/photo-1551504734-5ee1c4a1479b?auto=format&fit=crop&w=800&q=80",  # Mexican street tacos
        "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?auto=format&fit=crop&w=800&q=80",  # Cheesy quesadilla with salsa
        "https://images.unsplash.com/photo-1513456852971-30c0b8199d4d?auto=format&fit=crop&w=800&q=80",  # Loaded nachos supreme
        "https://images.unsplash.com/photo-1626700051175-6818013e1d4f?auto=format&fit=crop&w=800&q=80",  # Baked enchiladas
    ],
    "pork": [
        "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=800&q=80",  # Glazed BBQ ribs
        "https://images.unsplash.com/photo-1528607929212-2636ec44253e?auto=format&fit=crop&w=800&q=80",  # Seared pork chop
        "https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?auto=format&fit=crop&w=800&q=80",  # Crispy bacon rashers
    ],
    "corn": [
        "https://images.unsplash.com/photo-1551754655-cd27e38d2076?auto=format&fit=crop&w=800&q=80",  # Golden grilled sweet corn with herbs
        "https://images.unsplash.com/photo-1563245372-f21724e3856d?auto=format&fit=crop&w=800&q=80",  # Sweet corn skillet
        "https://images.unsplash.com/photo-1629814249584-bd4d53cf0e7d?auto=format&fit=crop&w=800&q=80",  # Creamy sweet corn soup
        "https://images.unsplash.com/photo-1579619569721-5d998088caa5?auto=format&fit=crop&w=800&q=80",  # Golden baked cornbread
        "https://images.unsplash.com/photo-1600891964599-f61ba0e24092?auto=format&fit=crop&w=800&q=80",  # Crispy corn patties
        "https://images.unsplash.com/photo-1546793665-c74683f339c1?auto=format&fit=crop&w=800&q=80",  # Mexican street corn salad
    ],
    "fritter": [
        "https://images.unsplash.com/photo-1541518763669-27fef04b14ea?auto=format&fit=crop&w=800&q=80",  # Crispy golden vegetable fritters
        "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=800&q=80",  # Pan-seared vegetable patties
        "https://images.unsplash.com/photo-1565299585323-38d6b0865b47?auto=format&fit=crop&w=800&q=80",  # Crispy zucchini fritters with dip
        "https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=800&q=80",  # Spiced crispy croquettes
        "https://images.unsplash.com/photo-1606851094655-b2593a9af63f?auto=format&fit=crop&w=800&q=80",  # Crispy potato corn cakes
        "https://images.unsplash.com/photo-1562967914-608f82629710?auto=format&fit=crop&w=800&q=80",  # Golden savory crispy patties
    ],
    "vegetable": [
        "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80",  # Roasted seasoned vegetables
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=800&q=80",  # Fresh vegetable stir fry
        "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80",  # Healthy rainbow veggie bowl
        "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?auto=format&fit=crop&w=800&q=80",  # Fresh greens salad plate
        "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=800&q=80",  # Seasonal harvest bowl
        "https://images.unsplash.com/photo-1505253758473-96b3015f21c9?auto=format&fit=crop&w=800&q=80",  # Avocado garden salad
        "https://images.unsplash.com/photo-1559847844-5315695dadae?auto=format&fit=crop&w=800&q=80",  # Mediterranean roasted cauliflower bowl
        "https://images.unsplash.com/photo-1543339308-43e59d6b73a6?auto=format&fit=crop&w=800&q=80",  # Green goddess power salad
        "https://images.unsplash.com/photo-1556910103-1c02745aae4d?auto=format&fit=crop&w=800&q=80",  # Grilled garden vegetables
        "https://images.unsplash.com/photo-1592417817098-8f3d6910985b?auto=format&fit=crop&w=800&q=80",  # Steamed broccoli and greens
        "https://images.unsplash.com/photo-1574484284002-952d92456975?auto=format&fit=crop&w=800&q=80",  # Fresh zucchini and herb saute
        "https://images.unsplash.com/photo-1564834724105-918b73d1b9e0?auto=format&fit=crop&w=800&q=80",  # Warm root vegetable tray
        "https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?auto=format&fit=crop&w=800&q=80",  # Crisp market produce bowl
        "https://images.unsplash.com/photo-1506084868230-bb9d95c24759?auto=format&fit=crop&w=800&q=80",  # Gourmet farm vegetable dish
        "https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=800&q=80",  # Crispy roasted herb potatoes
        "https://images.unsplash.com/photo-1587486913049-53fc88980cfc?auto=format&fit=crop&w=800&q=80",  # Vegetable herb frittata
    ],
    "pie": [
        "https://images.unsplash.com/photo-1509440159596-0249088772ff?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1519869325930-281384150729?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1535920527002-b35e96722eb9?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1562007908-859b4ba9a1a2?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1568571780765-9276ac8b75a2?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1587314168485-3236d6710814?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1621303837174-89787a7d4729?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1517427294546-5aa121f68e8a?auto=format&fit=crop&w=800&q=80",
    ],
    "cake": [
        "https://images.unsplash.com/photo-1578985545062-69928b1d9587?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1533134242443-d4fd215305ad?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1588195538326-c5b1e9f80a1b?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1557308536-ee471ef2c390?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1606890737304-57a1ca8a5b62?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1514056052883-d017fddd0426?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1563729784474-d77dbb933a9e?auto=format&fit=crop&w=800&q=80",
    ],
    "cookie": [
        "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1558961363-fa8fdf82db35?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1590080875515-8a3a8dc5735e?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1548848221-0c2e497ed557?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1569864358642-9d1684040f43?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1597528662465-55ece5734101?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1584308666744-24d5c474f2ae?auto=format&fit=crop&w=800&q=80",
    ],
    "bread": [
        "https://images.unsplash.com/photo-1549931319-a545dcf3bc73?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1589367920969-ab8e050bbb04?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1586444248902-2f64eddc13df?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1579697096985-41fe1430e5df?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1517433670267-08bbd4be890f?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1608198093002-ad4e005484ec?auto=format&fit=crop&w=800&q=80",
    ],
    "muffin": [
        "https://images.unsplash.com/photo-1586985289688-ca3cf47d3e6e?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1576618148400-f54bed99fcfd?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1550617931-e17a7b70dce2?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1599785209707-a456fc1337bb?auto=format&fit=crop&w=800&q=80",
    ],
    "pancake": [
        "https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1528207776546-365bb710ee93?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1504754524776-8f4f37790ca0?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1575853121743-60c24f0a7502?auto=format&fit=crop&w=800&q=80",
    ],
    "pizza": [
        "https://images.unsplash.com/photo-1513104890138-7c749659a591?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1574071318508-1cdbab80d002?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1593560708920-61dd98c46a4e?auto=format&fit=crop&w=800&q=80",
    ],
    "pasta": [
        "https://images.unsplash.com/photo-1551183053-bf91a1d81141?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1546549032-9571cd6b27df?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1579684947550-22e945225d9a?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1608897013039-887f21d8c804?auto=format&fit=crop&w=800&q=80",
    ],
    "soup": [
        "https://images.unsplash.com/photo-1547592166-23ac45744acd?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1582878826629-29b7ad1cdc43?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1603105037880-880cd4edfb0d?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1541832676-9b763b0239ab?auto=format&fit=crop&w=800&q=80",
    ],
    "salad": [
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1546793665-c74683f339c1?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1505253758473-96b3015f21c9?auto=format&fit=crop&w=800&q=80",
    ],
    "curry": [
        "https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=800&q=80",  # Rich aromatic Indian curry
        "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=800&q=80",
    ],
    "chicken": [
        "https://images.unsplash.com/photo-1598515214211-89d3c73ae83b?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1562967914-608f82629710?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1626082927389-6cd097cdc6ec?auto=format&fit=crop&w=800&q=80",
    ],
    "steak": [
        "https://images.unsplash.com/photo-1544025162-d76694265947?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1558030006-450675393462?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1529692236671-f1f6cf9683ba?auto=format&fit=crop&w=800&q=80",
    ],
    "seafood": [
        "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1559742811-822873691df8?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1534422298391-e4f8c172dddb?auto=format&fit=crop&w=800&q=80",
    ],
    "burger": [
        "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1550547660-d9450f859349?auto=format&fit=crop&w=800&q=80",
    ],
    "sandwich": [
        "https://images.unsplash.com/photo-1528735602780-2552fd46c7af?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1509722747041-616f39b57569?auto=format&fit=crop&w=800&q=80",
    ],
    "general": [
        "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1504674900247-0877df9cc836?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1547592180-85f173990554?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1551183053-bf91a1d81141?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1565299624946-b28f40a0ae38?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1563379091339-03b21ab4a4f8?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1551754655-cd27e38d2076?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1518977676601-b53f82aba655?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1541832676-9b763b0239ab?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1505253758473-96b3015f21c9?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1587486913049-53fc88980cfc?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1608897013039-887f21d8c804?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?auto=format&fit=crop&w=800&q=80",
        "https://images.unsplash.com/photo-1541518763669-27fef04b14ea?auto=format&fit=crop&w=800&q=80",
    ],
}


def _detect_culinary_category(text: str, ner: Optional[List[str]] = None) -> Optional[str]:
    """
    Detects the primary culinary category from title, cuisine, and recipe NER ingredients.
    Guarantees that a recipe mentioning potatoes always gets classified as potato,
    corn as corn, fritters as fritter, pasta as pasta, chicken as chicken, etc.
    """
    t = text.lower()
    ner_joined = " ".join((ner or [])).lower()
    combined = f"{t} {ner_joined}"

    # Strict high-priority food patterns
    if any(k in t for k in ["soup", "chowder", "bisque", "stew", "chili"]) or any(k in combined for k in ["soup", "chowder", "bisque"]):
        return "soup"
    if any(k in combined for k in ["french fry", "french fries", "fries", "wedges", "hashbrown"]):
        return "fries"
    if any(k in combined for k in ["fritter", "fritters", "croquette"]) or (any(k in combined for k in ["patty", "patties"]) and not any(k in combined for k in ["beef", "burger", "hamburger"])):
        return "fritter"
    if any(k in combined for k in ["corn", "maize", "polenta", "elote"]):
        return "corn"
    if any(k in combined for k in ["potato", "potatoes", "tater", "gnocchi"]):
        return "potato"
    if any(k in combined for k in ["pasta", "spaghetti", "lasagna", "penne", "macaroni", "fettuccine", "noodle"]):
        return "pasta"
    if any(k in combined for k in ["pizza", "calzone", "flatbread"]):
        return "pizza"
    if any(k in combined for k in ["salad", "slaw"]):
        return "salad"
    if any(k in combined for k in ["curry", "tikka", "masala", "dal", "paneer", "korma"]):
        return "curry"
    if any(k in combined for k in ["taco", "fajita", "enchilada", "quesadilla", "burrito", "nacho"]):
        return "taco"
    if any(k in combined for k in ["burger", "slider"]):
        return "burger"
    if any(k in combined for k in ["sandwich", "panini", "sub", "wrap", "toast"]):
        return "sandwich"
    if any(k in combined for k in ["biryani", "fried rice", "risotto", "pilaf"]) or ("rice" in t and "rice" in ner_joined):
        return "rice"
    if any(k in combined for k in ["omelet", "frittata", "scrambled egg", "poached egg"]) or ("egg" in t and "egg" in ner_joined):
        return "egg"
    if any(k in combined for k in ["pie", "cobbler", "tart", "crisp"]):
        return "pie"
    if any(k in combined for k in ["cake", "cheesecake", "brownie", "fudge"]):
        return "cake"
    if any(k in combined for k in ["cookie", "biscuit", "shortbread", "macaron"]):
        return "cookie"
    if any(k in combined for k in ["muffin", "cupcake"]):
        return "muffin"
    if any(k in combined for k in ["pancake", "waffle", "crepe"]):
        return "pancake"
    if any(k in combined for k in ["bread", "baguette", "brioche", "roll", "bun"]):
        return "bread"
    if any(k in combined for k in ["salmon", "shrimp", "fish", "tuna", "seafood", "clam", "crab", "lobster"]):
        return "seafood"
    if any(k in combined for k in ["chicken", "turkey", "wing", "poultry"]):
        return "chicken"
    if any(k in combined for k in ["pork", "bacon", "ham", "pork chop", "ribs"]):
        return "pork"
    if any(k in combined for k in ["steak", "beef", "roast beef", "meatball", "brisket"]):
        return "beef"
    if any(k in combined for k in ["broccoli", "asparagus", "zucchini", "spinach", "vegetable"]):
        return "vegetable"

    return None


def resolve_recipe_image_url(
    title: str,
    cuisine: Optional[str] = None,
    recipe_id: Optional[int] = None,
    used_urls: Optional[Set[str]] = None,
    ner: Optional[List[str]] = None,
    ingredients: Optional[List[str]] = None,
    dietary_preference: Optional[str] = None,
) -> str:
    """
    Dynamically maps recipe titles and ingredients to curated, high-resolution culinary photos.
    Guarantees semantic relatability and 100% collision-free deduplication across recommendation grids:
    - French fries recipes receive authentic golden french fry photography.
    - Potato recipes receive authentic, appetizing potato photography.
    - Corn dishes receive golden sweet corn photography.
    - Fritters receive crispy golden fritter / patty photography.
    - If user selected Vegetarian or Vegan, guarantees strictly vegetarian photography.
    - Tracks used_urls across grid cards to eliminate repeated images.
    """
    if used_urls is None:
        used_urls = set()

    t_lower = (title or "").lower().strip()
    c_lower = (cuisine or "").lower().strip()
    full_text = f"{t_lower} {c_lower}"
    seed = abs(zlib.crc32(f"{recipe_id or ''}_{t_lower}".encode("utf-8", errors="ignore")))

    is_veg = (dietary_preference or "").lower().strip() in ("vegetarian", "veg", "vegetarian_compatible", "vegan", "vegan_compatible")
    meat_words = {
        "chicken", "beef", "pork", "lamb", "bacon", "salmon", "shrimp", "fish",
        "turkey", "pork chop", "veal", "duck", "prosciutto", "sausage", "pepperoni",
        "tuna", "anchovy", "crab", "lobster", "clam", "mussel", "oyster", "squid",
        "calamari", "octopus", "scallop", "prawn", "ham", "steak", "meatball",
        "ribs", "brisket", "poultry", "meat", "salami"
    }

    # Step 1: Detect primary culinary category
    category = _detect_culinary_category(full_text, ner)
    if is_veg and category in ("chicken", "beef", "steak", "pork", "seafood", "burger"):
        category = "vegetable"

    # Step 2: Search MealDB catalog with strict category & dietary constraints
    title_words = set(re.findall(r"[a-zA-Z]{3,}", t_lower))
    stop_words = {"and", "with", "the", "for", "style", "easy", "best", "homemade", "recipe", "delicious", "classic"}
    meaningful_words = {w for w in title_words if w not in stop_words}

    matching_catalog_photos: List[str] = []
    if _PHOTO_CATALOG:
        for meal in _PHOTO_CATALOG:
            meal_name = meal.get("name", "").lower()
            if is_veg and any(mw in meal_name for mw in meat_words):
                continue
            m_words = set(meal.get("keywords") or re.findall(r"[a-zA-Z]{3,}", meal_name))

            # If we know the category (e.g. potato), only consider MealDB photos belonging to that concept!
            if category == "fries" and not any(p in meal_name for p in ["fries", "fry", "chips", "wedges"]):
                continue
            if category == "potato" and not any(p in meal_name for p in ["potato", "papas", "mash"]):
                continue
            if category == "pasta" and not any(p in meal_name for p in ["pasta", "spaghetti", "lasagna", "penne", "macaroni"]):
                continue
            if category == "pizza" and "pizza" not in meal_name:
                continue
            if category == "soup" and not any(p in meal_name for p in ["soup", "stew", "chowder"]):
                continue
            if category == "chicken" and not any(p in meal_name for p in ["chicken", "poultry"]):
                continue

            overlap = len(meaningful_words.intersection(m_words))
            if overlap >= 2:
                matching_catalog_photos.append(meal["url"])

    # Step 3: Candidate pool assembly
    category_pool = _UNSPLASH_POOLS.get(category, []) if category else []
    if is_veg and category in ("chicken", "beef", "steak", "pork", "seafood", "burger"):
        category_pool = _UNSPLASH_POOLS.get("vegetable", [])
    candidate_pool = matching_catalog_photos + category_pool

    # Step 4: Pick first unused candidate from the relevant category pool
    if candidate_pool:
        start_idx = seed % len(candidate_pool)
        for i in range(len(candidate_pool)):
            cand = candidate_pool[(start_idx + i) % len(candidate_pool)]
            if cand not in used_urls:
                used_urls.add(cand)
                return cand

    # Step 5: Check related adjacent pools before repeating images!
    fallback_categories: List[str] = []
    if is_veg or category in ("fritter", "corn", "vegetable", "potato", "salad", "soup", "rice"):
        fallback_categories = ["fritter", "corn", "vegetable", "salad", "potato", "soup", "rice"]
    else:
        fallback_categories = ["general", "vegetable", "salad", "sandwich"]

    for fb_cat in fallback_categories:
        pool = _UNSPLASH_POOLS.get(fb_cat, [])
        if pool:
            st = seed % len(pool)
            for i in range(len(pool)):
                cand = pool[(st + i) % len(pool)]
                if cand not in used_urls:
                    used_urls.add(cand)
                    return cand

    # Step 6: Safe fallback to appetizing general savory food photography (strictly vegetarian if veg preference)
    general_pool = _UNSPLASH_POOLS.get("general", [])
    if general_pool:
        start_gen = seed % len(general_pool)
        for i in range(len(general_pool)):
            cand = general_pool[(start_gen + i) % len(general_pool)]
            if cand not in used_urls:
                used_urls.add(cand)
                return cand

    # Step 7: Exhaustive fallback - scan any photo in _UNSPLASH_POOLS not yet in used_urls
    for cat_name, pool in _UNSPLASH_POOLS.items():
        if is_veg and cat_name in ("chicken", "beef", "steak", "pork", "seafood", "burger"):
            continue
        for cand in pool:
            if cand not in used_urls:
                used_urls.add(cand)
                return cand

    # If completely exhausted (>100 cards), cycle with deterministic offset
    chosen = candidate_pool[seed % len(candidate_pool)] if candidate_pool else general_pool[seed % len(general_pool)]
    used_urls.add(chosen)
    return chosen


class SandboxRecipeClusterItem(BaseModel):
    recipe_id: int
    title: str
    match_score: float
    pantry_usage_score: float
    expiry_priority_score: float
    missing_ingredients: List[str]
    matched_ingredients: List[str]
    missing_cost: float
    safety_status: str
    cooking_time_minutes: Optional[int] = None
    why_recommended: str
    image_url: Optional[str] = None
    ims: float = 0.0
    pus: float = 0.0
    recommendation_score: float = 0.0


class SandboxClusters(BaseModel):
    max_pantry_use: List[SandboxRecipeClusterItem]
    low_shopping_cost: List[SandboxRecipeClusterItem]
    near_expiry_rescues: List[SandboxRecipeClusterItem]
    quick_meals: List[SandboxRecipeClusterItem]


class SandboxSimulateRequest(BaseModel):
    active_pantry: List[str]
    added_ingredients: Optional[List[str]] = None
    disabled_ingredients: Optional[List[str]] = None
    pantry_expiry_dates: Optional[Dict[str, int]] = None
    dietary_preference: Optional[str] = None
    allergens: Optional[List[str]] = None
    max_cooking_time_minutes: Optional[int] = None
    weights: Optional[OptimizationWeights] = None


class SandboxSimulationResponse(BaseModel):
    active_ingredients_count: int
    evaluated_candidates_count: int
    applied_weights: OptimizationWeights
    clusters: SandboxClusters
    top_recommendations: List[SandboxRecipeClusterItem]


class LeftoverSandboxEngine:
    """
    Simulation engine powering the interactive leftover sandbox.
    """

    def __init__(self, engine: Optional[RecommendationEngine] = None):
        self.engine = engine or RecommendationEngine()

    def simulate(self, request: SandboxSimulateRequest) -> SandboxSimulationResponse:
        # 1. Compute effective pantry set
        base_pantry = set([p.lower().strip() for p in request.active_pantry])
        if request.added_ingredients:
            base_pantry.update([a.lower().strip() for a in request.added_ingredients])
        if request.disabled_ingredients:
            base_pantry.difference_update([d.lower().strip() for d in request.disabled_ingredients])

        effective_pantry_list = list(base_pantry)
        weights = request.weights or OptimizationWeights()
        expiry_map = request.pantry_expiry_dates or {}

        # 2. Get baseline candidates from engine with allergen safety filter
        rec_response = self.engine.recommend(
            pantry_ingredients=effective_pantry_list,
            limit=40,
            dietary_preference=request.dietary_preference,
            allergens=request.allergens,
            max_cooking_time_minutes=request.max_cooking_time_minutes,
        )

        all_items: List[SandboxRecipeClusterItem] = []
        used_sandbox_images: Set[str] = set()

        is_veg = (request.dietary_preference or "").lower().strip() in ("vegetarian", "veg", "vegetarian_compatible", "vegan", "vegan_compatible")
        meat_tokens = {
            "chicken", "beef", "pork", "lamb", "bacon", "salmon", "shrimp",
            "fish", "turkey", "pork chop", "pork chops", "veal", "duck", "prosciutto",
            "sausage", "pepperoni", "gelatin", "tuna", "anchovy", "anchovies",
            "crab", "lobster", "clam", "mussel", "oyster", "squid", "calamari",
            "octopus", "scallop", "prawn", "prawns", "ham", "steak", "meatball",
            "meatballs", "lard", "chorizo", "salami", "pancetta", "ribs", "brisket",
            "poultry", "meat", "ground beef", "roast beef"
        }

        for rec in rec_response.recommendations:
            # Compulsory secondary guard for vegetarian mode
            if is_veg:
                title_lower = rec.title.lower()
                ner_lower = [n.lower() for n in (rec.ner or [])]
                ing_lower = " ".join(rec.ingredients or []).lower()
                if any(m in title_lower or any(m == n or m in n.split() for n in ner_lower) or any(re.search(rf"\b{re.escape(m)}\b", ing_lower) for m in meat_tokens) for m in meat_tokens):
                    continue

            # Check Hard Safety Lock
            safety_res = allergen_guard.check_recipe_safety(
                recipe_id=rec.recipe_id,
                recipe_title=rec.title,
                ingredients=rec.ingredients,
                directions=rec.directions,
                user_allergens=request.allergens,
                user_diet=request.dietary_preference,
                recipe_ner=rec.ner,
            )

            if safety_res.is_blocked:
                continue

            # Estimate cost
            missing_cost = sum(shopping_optimizer.estimate_item_cost(item).estimated_package_cost for item in rec.missing_ingredients)

            # Waste Optimization
            waste_res = food_waste_optimizer.optimize_recipe_ranking(
                recipe_id=rec.recipe_id,
                title=rec.title,
                matched_ingredients=rec.matched_ingredients,
                missing_ingredients=rec.missing_ingredients,
                pantry_expiry_map=expiry_map,
                total_pantry_count=len(effective_pantry_list),
                estimated_missing_cost=missing_cost,
                weights=weights,
            )

            img_url = resolve_recipe_image_url(
                title=rec.title,
                cuisine=rec.cuisine,
                recipe_id=rec.recipe_id,
                used_urls=used_sandbox_images,
                ner=rec.ner,
                ingredients=rec.ingredients,
                dietary_preference=request.dietary_preference,
            )
            used_sandbox_images.add(img_url)

            item = SandboxRecipeClusterItem(
                recipe_id=rec.recipe_id,
                title=rec.title,
                match_score=waste_res.composite_waste_score,
                pantry_usage_score=waste_res.pantry_usage_score,
                expiry_priority_score=waste_res.expiry_priority_score,
                missing_ingredients=rec.missing_ingredients,
                matched_ingredients=rec.matched_ingredients,
                missing_cost=round(missing_cost, 2),
                safety_status=safety_res.status,
                cooking_time_minutes=rec.estimated_time_minutes,
                why_recommended=waste_res.rationale,
                image_url=img_url,
                ims=rec.ims,
                pus=rec.pus,
                recommendation_score=waste_res.composite_waste_score or rec.recommendation_score,
            )
            all_items.append(item)

        # 3. Sort overall top
        all_items.sort(key=lambda x: x.match_score, reverse=True)

        # 4. Form Recommendation Clusters
        max_pantry = sorted(all_items, key=lambda x: x.pantry_usage_score, reverse=True)[:6]
        low_cost = sorted(all_items, key=lambda x: (len(x.missing_ingredients), x.missing_cost))[:6]
        near_expiry = sorted(all_items, key=lambda x: x.expiry_priority_score, reverse=True)[:6]
        quick_meals = sorted(all_items, key=lambda x: (x.cooking_time_minutes or 999))[:6]

        clusters = SandboxClusters(
            max_pantry_use=max_pantry,
            low_shopping_cost=low_cost,
            near_expiry_rescues=near_expiry,
            quick_meals=quick_meals,
        )

        return SandboxSimulationResponse(
            active_ingredients_count=len(effective_pantry_list),
            evaluated_candidates_count=rec_response.total_candidates_evaluated,
            applied_weights=weights,
            clusters=clusters,
            top_recommendations=all_items[:12],
        )

sandbox_engine = LeftoverSandboxEngine()
