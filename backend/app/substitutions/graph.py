"""
backend/app/substitutions/graph.py

Dynamic Smart Substitution Graph using NetworkX and SQLite.
Builds an explicit, multi-relational ingredient knowledge graph with rich attributes
(flavor, texture, acidity, fat/protein, cooking roles, dietary tags, allergens)
and multi-relational edges (SUBSTITUTES, SAME_COOKING_ROLE, SIMILAR_FLAVOR, SIMILAR_TEXTURE, COMBINES_WITH).

Supports:
  1. Persistent storage in SQLite (recipe_metadata.sqlite).
  2. Single-node substitutions with verified ratios & evidence.
  3. Dynamic multi-ingredient functional combinations (e.g. baking soda + yogurt for baking powder).
  4. Attribute & role-based dynamic graph traversal for unindexed ingredients.
  5. Deterministic allergen and dietary safety hard-locks.
  6. Pantry-aware ranking bonus for on-hand ingredients.
  7. Graceful handling of missing/incomplete attributes without crashing.
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from backend.app.config import settings
from backend.app.safety.allergen_guard import ALLERGEN_TAXONOMY
from backend.app.substitutions.knowledge_base import SUBSTITUTION_DATABASE
from backend.app.substitutions.models import SubstitutionCandidate, SubstitutionEntry
from backend.app.substitutions.normalizer import (
    INGREDIENT_ALIASES,
    normalize_ingredient_token,
    resolve_canonical_ingredient,
)

logger = logging.getLogger(__name__)


# Standard default ingredient attributes seed dataset
DEFAULT_INGREDIENT_NODES: List[Dict[str, Any]] = [
    # --- Dairy & Dairy Alternatives ---
    {
        "canonical_name": "butter",
        "aliases": ["unsalted butter", "salted butter", "sweet cream butter"],
        "category": "fats_oils",
        "flavor_profile": "rich_creamy",
        "texture": "solid_fat",
        "cooking_role": "fat_moisture",
        "acidity": 0.0,
        "fat_content": 81.0,
        "protein_content": 1.0,
        "dietary_compatibility": ["vegetarian"],
        "allergens": ["dairy"],
        "cuisine_compatibility": ["American", "French", "Italian", "Indian", "European"],
    },
    {
        "canonical_name": "margarine",
        "aliases": ["vegan butter", "plant butter", "dairy-free margarine"],
        "category": "fats_oils",
        "flavor_profile": "neutral_salty",
        "texture": "solid_fat",
        "cooking_role": "fat_moisture",
        "acidity": 0.0,
        "fat_content": 80.0,
        "protein_content": 0.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["American", "European"],
    },
    {
        "canonical_name": "olive oil",
        "aliases": ["extra virgin olive oil", "evoo", "pure olive oil"],
        "category": "fats_oils",
        "flavor_profile": "fruity_savory",
        "texture": "liquid_fat",
        "cooking_role": "fat_frying",
        "acidity": 0.0,
        "fat_content": 100.0,
        "protein_content": 0.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["Mediterranean", "Italian", "Spanish", "Greek"],
    },
    {
        "canonical_name": "vegetable oil",
        "aliases": ["canola oil", "cooking oil", "corn oil", "sunflower oil", "oil"],
        "category": "fats_oils",
        "flavor_profile": "neutral",
        "texture": "liquid_fat",
        "cooking_role": "fat_frying",
        "acidity": 0.0,
        "fat_content": 100.0,
        "protein_content": 0.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "milk",
        "aliases": ["whole milk", "skim milk", "2% milk", "cow milk"],
        "category": "dairy",
        "flavor_profile": "creamy_mild",
        "texture": "liquid",
        "cooking_role": "liquid_moisture",
        "acidity": 0.1,
        "fat_content": 3.2,
        "protein_content": 3.4,
        "dietary_compatibility": ["vegetarian"],
        "allergens": ["dairy"],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "soy milk",
        "aliases": ["unsweetened soy milk", "plain soy milk"],
        "category": "dairy_alternative",
        "flavor_profile": "neutral_nutty",
        "texture": "liquid",
        "cooking_role": "liquid_moisture",
        "acidity": 0.1,
        "fat_content": 2.0,
        "protein_content": 3.3,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": ["soy"],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "almond milk",
        "aliases": ["unsweetened almond milk"],
        "category": "dairy_alternative",
        "flavor_profile": "nutty_sweet",
        "texture": "thin_liquid",
        "cooking_role": "liquid_moisture",
        "acidity": 0.1,
        "fat_content": 1.1,
        "protein_content": 0.5,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": ["tree_nuts"],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "oat milk",
        "aliases": ["plain oat milk"],
        "category": "dairy_alternative",
        "flavor_profile": "creamy_oat",
        "texture": "creamy_liquid",
        "cooking_role": "liquid_thickener",
        "acidity": 0.1,
        "fat_content": 1.5,
        "protein_content": 1.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "plain greek yogurt",
        "aliases": ["yogurt", "greek yogurt", "plain yogurt", "curd", "dahi"],
        "category": "dairy",
        "flavor_profile": "tangy_cultured",
        "texture": "thick_cream",
        "cooking_role": "binder_moisture_acid",
        "acidity": 0.6,
        "fat_content": 5.0,
        "protein_content": 10.0,
        "dietary_compatibility": ["vegetarian"],
        "allergens": ["dairy"],
        "cuisine_compatibility": ["Mediterranean", "Indian", "American"],
    },
    {
        "canonical_name": "heavy cream",
        "aliases": ["heavy whipping cream", "whipping cream", "double cream"],
        "category": "dairy",
        "flavor_profile": "rich_fat",
        "texture": "viscous_fat",
        "cooking_role": "fat_thickener",
        "acidity": 0.1,
        "fat_content": 36.0,
        "protein_content": 2.0,
        "dietary_compatibility": ["vegetarian"],
        "allergens": ["dairy"],
        "cuisine_compatibility": ["French", "Italian", "American", "Indian"],
    },
    {
        "canonical_name": "sour cream",
        "aliases": ["crema", "cultured cream"],
        "category": "dairy",
        "flavor_profile": "tangy_cultured",
        "texture": "thick_cream",
        "cooking_role": "acid_fat",
        "acidity": 0.6,
        "fat_content": 19.0,
        "protein_content": 2.5,
        "dietary_compatibility": ["vegetarian"],
        "allergens": ["dairy"],
        "cuisine_compatibility": ["Mexican", "American", "Eastern European"],
    },
    {
        "canonical_name": "buttermilk",
        "aliases": ["cultured buttermilk"],
        "category": "dairy",
        "flavor_profile": "tangy_acidic",
        "texture": "thin_cultured",
        "cooking_role": "acid_leavener",
        "acidity": 0.8,
        "fat_content": 2.0,
        "protein_content": 3.0,
        "dietary_compatibility": ["vegetarian"],
        "allergens": ["dairy"],
        "cuisine_compatibility": ["American", "Southern", "Baking"],
    },

    # --- Leaveners, Acids & Binders ---
    {
        "canonical_name": "baking powder",
        "aliases": ["double acting baking powder"],
        "category": "leavener",
        "flavor_profile": "neutral_alkaline",
        "texture": "fine_powder",
        "cooking_role": "chemical_leavener",
        "acidity": 0.0,
        "fat_content": 0.0,
        "protein_content": 0.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["Baking", "American", "European"],
    },
    {
        "canonical_name": "baking soda",
        "aliases": ["sodium bicarbonate", "bicarb soda"],
        "category": "leavener",
        "flavor_profile": "alkaline_salty",
        "texture": "fine_powder",
        "cooking_role": "base_leavener",
        "acidity": 0.0,
        "fat_content": 0.0,
        "protein_content": 0.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["Baking"],
    },
    {
        "canonical_name": "cream of tartar",
        "aliases": ["potassium bitartrate"],
        "category": "acid",
        "flavor_profile": "tart_acidic",
        "texture": "fine_powder",
        "cooking_role": "powder_acid",
        "acidity": 0.9,
        "fat_content": 0.0,
        "protein_content": 0.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["Baking"],
    },
    {
        "canonical_name": "lemon juice",
        "aliases": ["fresh lemon juice", "lemon"],
        "category": "citrus_acid",
        "flavor_profile": "citrus_tart",
        "texture": "liquid",
        "cooking_role": "acid_brightener",
        "acidity": 0.9,
        "fat_content": 0.0,
        "protein_content": 0.3,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "white vinegar",
        "aliases": ["distilled vinegar", "vinegar"],
        "category": "acid",
        "flavor_profile": "sharp_acidic",
        "texture": "liquid",
        "cooking_role": "acid_leavener",
        "acidity": 1.0,
        "fat_content": 0.0,
        "protein_content": 0.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "egg",
        "aliases": ["eggs", "large egg", "whole egg"],
        "category": "binder_protein",
        "flavor_profile": "rich_savory",
        "texture": "viscous_binder",
        "cooking_role": "binder_leavener",
        "acidity": 0.0,
        "fat_content": 10.0,
        "protein_content": 13.0,
        "dietary_compatibility": ["vegetarian"],
        "allergens": ["egg"],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "flax egg",
        "aliases": ["ground flaxseed", "flaxseed meal", "chia egg"],
        "category": "binder_alternative",
        "flavor_profile": "nutty_grain",
        "texture": "gelatinous_binder",
        "cooking_role": "binder_moisture",
        "acidity": 0.0,
        "fat_content": 8.0,
        "protein_content": 4.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["Baking"],
    },
    {
        "canonical_name": "applesauce",
        "aliases": ["unsweetened applesauce", "apple puree"],
        "category": "fruit_puree",
        "flavor_profile": "sweet_apple",
        "texture": "puree",
        "cooking_role": "moisture_binder",
        "acidity": 0.3,
        "fat_content": 0.2,
        "protein_content": 0.2,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["Baking"],
    },

    # --- Flours & Grains ---
    {
        "canonical_name": "all-purpose flour",
        "aliases": ["flour", "plain flour", "white flour", "ap flour"],
        "category": "flour_starch",
        "flavor_profile": "neutral_wheat",
        "texture": "fine_powder",
        "cooking_role": "structure_binder",
        "acidity": 0.0,
        "fat_content": 1.0,
        "protein_content": 10.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": ["gluten", "wheat"],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "gluten-free flour",
        "aliases": ["1-to-1 baking flour", "gf flour blend"],
        "category": "flour_starch",
        "flavor_profile": "neutral",
        "texture": "fine_powder",
        "cooking_role": "structure_binder",
        "acidity": 0.0,
        "fat_content": 1.0,
        "protein_content": 4.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "cornstarch",
        "aliases": ["corn flour", "maize starch"],
        "category": "thickener",
        "flavor_profile": "neutral",
        "texture": "fine_powder",
        "cooking_role": "thickener",
        "acidity": 0.0,
        "fat_content": 0.0,
        "protein_content": 0.3,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["All"],
    },

    # --- Aromatics & Alliums ---
    {
        "canonical_name": "garlic",
        "aliases": ["garlic cloves", "fresh garlic", "minced garlic"],
        "category": "aromatics",
        "flavor_profile": "pungent_allium",
        "texture": "solid",
        "cooking_role": "aromatic_flavor",
        "acidity": 0.1,
        "fat_content": 0.5,
        "protein_content": 6.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "garlic powder",
        "aliases": ["granulated garlic"],
        "category": "spice",
        "flavor_profile": "pungent_allium",
        "texture": "fine_powder",
        "cooking_role": "aromatic_flavor",
        "acidity": 0.1,
        "fat_content": 0.5,
        "protein_content": 16.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "onion",
        "aliases": ["yellow onion", "white onion", "red onion", "sweet onion", "onions"],
        "category": "aromatics",
        "flavor_profile": "savory_sweet_pungent",
        "texture": "crisp_solid",
        "cooking_role": "aromatic_base",
        "acidity": 0.1,
        "fat_content": 0.1,
        "protein_content": 1.1,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "shallot",
        "aliases": ["shallots", "french shallots"],
        "category": "aromatics",
        "flavor_profile": "delicate_sweet_allium",
        "texture": "crisp_solid",
        "cooking_role": "aromatic_base",
        "acidity": 0.1,
        "fat_content": 0.1,
        "protein_content": 2.5,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["French", "Asian", "European"],
    },
    {
        "canonical_name": "green onion",
        "aliases": ["scallions", "scallion", "spring onion", "chives"],
        "category": "aromatics",
        "flavor_profile": "fresh_mild_allium",
        "texture": "crisp_leafy",
        "cooking_role": "aromatic_garnish",
        "acidity": 0.1,
        "fat_content": 0.2,
        "protein_content": 1.8,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["Asian", "Mexican", "American"],
    },

    # --- Cheeses & Proteins ---
    {
        "canonical_name": "parmesan",
        "aliases": ["parmesan cheese", "parmigiano reggiano"],
        "category": "cheese",
        "flavor_profile": "savory_umami_salty",
        "texture": "hard_granular",
        "cooking_role": "umami_seasoning",
        "acidity": 0.2,
        "fat_content": 29.0,
        "protein_content": 35.0,
        "dietary_compatibility": ["vegetarian"],
        "allergens": ["dairy"],
        "cuisine_compatibility": ["Italian", "European", "American"],
    },
    {
        "canonical_name": "pecorino romano",
        "aliases": ["pecorino", "romano cheese"],
        "category": "cheese",
        "flavor_profile": "sharp_salty_sheep",
        "texture": "hard_granular",
        "cooking_role": "umami_seasoning",
        "acidity": 0.2,
        "fat_content": 32.0,
        "protein_content": 34.0,
        "dietary_compatibility": ["vegetarian"],
        "allergens": ["dairy"],
        "cuisine_compatibility": ["Italian"],
    },
    {
        "canonical_name": "nutritional yeast",
        "aliases": ["nooch"],
        "category": "seasoning",
        "flavor_profile": "cheesy_nutty_umami",
        "texture": "flaky_powder",
        "cooking_role": "umami_seasoning",
        "acidity": 0.1,
        "fat_content": 5.0,
        "protein_content": 45.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "mozzarella",
        "aliases": ["mozzarella cheese", "shredded mozzarella", "fresh mozzarella"],
        "category": "cheese",
        "flavor_profile": "mild_buttery_creamy",
        "texture": "elastic_melt",
        "cooking_role": "melting_cheese",
        "acidity": 0.1,
        "fat_content": 22.0,
        "protein_content": 22.0,
        "dietary_compatibility": ["vegetarian"],
        "allergens": ["dairy"],
        "cuisine_compatibility": ["Italian", "American"],
    },
    {
        "canonical_name": "provolone cheese",
        "aliases": ["provolone"],
        "category": "cheese",
        "flavor_profile": "mild_buttery_creamy",
        "texture": "elastic_melt",
        "cooking_role": "melting_cheese",
        "acidity": 0.1,
        "fat_content": 27.0,
        "protein_content": 25.0,
        "dietary_compatibility": ["vegetarian"],
        "allergens": ["dairy"],
        "cuisine_compatibility": ["Italian", "American"],
    },
    {
        "canonical_name": "chicken broth",
        "aliases": ["chicken stock", "bone broth"],
        "category": "stock",
        "flavor_profile": "savory_poultry_umami",
        "texture": "liquid",
        "cooking_role": "savory_liquid_base",
        "acidity": 0.1,
        "fat_content": 0.5,
        "protein_content": 1.5,
        "dietary_compatibility": ["non_vegetarian"],
        "allergens": [],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "vegetable broth",
        "aliases": ["vegetable stock", "veggie broth"],
        "category": "stock",
        "flavor_profile": "savory_vegetable_herb",
        "texture": "liquid",
        "cooking_role": "savory_liquid_base",
        "acidity": 0.1,
        "fat_content": 0.2,
        "protein_content": 0.5,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": [],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "ground beef",
        "aliases": ["minced beef", "hamburger"],
        "category": "meat",
        "flavor_profile": "savory_beef",
        "texture": "crumbled_protein",
        "cooking_role": "protein_main",
        "acidity": 0.0,
        "fat_content": 15.0,
        "protein_content": 26.0,
        "dietary_compatibility": ["non_vegetarian"],
        "allergens": [],
        "cuisine_compatibility": ["American", "Italian", "Mexican"],
    },
    {
        "canonical_name": "ground turkey",
        "aliases": ["ground chicken", "minced turkey"],
        "category": "meat",
        "flavor_profile": "savory_poultry",
        "texture": "crumbled_protein",
        "cooking_role": "protein_main",
        "acidity": 0.0,
        "fat_content": 8.0,
        "protein_content": 27.0,
        "dietary_compatibility": ["non_vegetarian"],
        "allergens": [],
        "cuisine_compatibility": ["All"],
    },
    {
        "canonical_name": "tofu",
        "aliases": ["extra firm tofu", "firm tofu", "bean curd"],
        "category": "plant_protein",
        "flavor_profile": "neutral_soya",
        "texture": "firm_protein_cube",
        "cooking_role": "protein_main",
        "acidity": 0.1,
        "fat_content": 4.8,
        "protein_content": 10.0,
        "dietary_compatibility": ["vegetarian", "vegan"],
        "allergens": ["soy"],
        "cuisine_compatibility": ["Asian", "Fusion"],
    },
    {
        "canonical_name": "paneer",
        "aliases": ["indian cottage cheese"],
        "category": "cheese_protein",
        "flavor_profile": "mild_milky",
        "texture": "firm_cube_non_melting",
        "cooking_role": "protein_main",
        "acidity": 0.1,
        "fat_content": 20.0,
        "protein_content": 18.0,
        "dietary_compatibility": ["vegetarian"],
        "allergens": ["dairy"],
        "cuisine_compatibility": ["Indian"],
    },
]


class IngredientSubstitutionGraph:
    """
    Dynamic Multi-Relational Knowledge Graph managing ingredient substitution networks.
    Stores and reads verified relationships from SQLite and dynamically generates,
    filters, and ranks suitable alternatives for every missing recipe ingredient.
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.METADATA_DB_PATH
        self.graph = nx.MultiDiGraph()
        self.functional_combinations: Dict[str, Dict[str, Any]] = {}
        self._initialize_storage_and_graph()

    def _initialize_storage_and_graph(self):
        """Ensures SQLite tables exist, seeds default graph data if empty, and loads NetworkX graph."""
        try:
            self._ensure_tables()
            self._seed_if_empty()
            self._load_from_sqlite()
        except Exception as e:
            logger.warning(f"Error initializing SQLite graph: {e}. Building in-memory fallback graph.")
            self._build_in_memory_fallback()

    def _ensure_tables(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingredient_nodes (
                canonical_name TEXT PRIMARY KEY,
                aliases TEXT,
                category TEXT,
                flavor_profile TEXT,
                texture TEXT,
                cooking_role TEXT,
                acidity REAL,
                fat_content REAL,
                protein_content REAL,
                dietary_compatibility TEXT,
                allergens TEXT,
                cuisine_compatibility TEXT
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingredient_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_ingredient TEXT NOT NULL,
                target_ingredient TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                ratio TEXT,
                confidence TEXT,
                context TEXT,
                reason TEXT,
                notes TEXT,
                source TEXT,
                is_verified INTEGER DEFAULT 1
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS functional_combinations (
                target_ingredient TEXT PRIMARY KEY,
                component_ingredients TEXT,
                acidic_options TEXT,
                ratio TEXT,
                reason TEXT,
                dietary_compatibility TEXT,
                allergens TEXT,
                context TEXT
            )
            """)
            conn.commit()

    def _seed_if_empty(self):
        with sqlite3.connect(str(self.db_path)) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM ingredient_nodes")
            count = cursor.fetchone()[0]
            if count == 0:
                logger.info("Seeding ingredient_nodes and relationships into SQLite database...")
                # Insert Base Nodes
                for node in DEFAULT_INGREDIENT_NODES:
                    cursor.execute("""
                    INSERT OR REPLACE INTO ingredient_nodes
                    (canonical_name, aliases, category, flavor_profile, texture, cooking_role,
                     acidity, fat_content, protein_content, dietary_compatibility, allergens, cuisine_compatibility)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        node["canonical_name"],
                        json.dumps(node.get("aliases", [])),
                        node.get("category", "general"),
                        node.get("flavor_profile", "general"),
                        node.get("texture", "general"),
                        node.get("cooking_role", "culinary"),
                        node.get("acidity", 0.0),
                        node.get("fat_content", 0.0),
                        node.get("protein_content", 0.0),
                        json.dumps(node.get("dietary_compatibility", ["vegetarian", "vegan"])),
                        json.dumps(node.get("allergens", [])),
                        json.dumps(node.get("cuisine_compatibility", ["All"])),
                    ))

                # Insert Verified Relationships from Curated Knowledge Base
                for entry in SUBSTITUTION_DATABASE:
                    orig = resolve_canonical_ingredient(entry.original_ingredient)
                    sub = resolve_canonical_ingredient(entry.substitute)
                    cursor.execute("""
                    INSERT INTO ingredient_relationships
                    (source_ingredient, target_ingredient, relationship_type, ratio, confidence, context, reason, notes, source, is_verified)
                    VALUES (?, ?, 'SUBSTITUTES', ?, ?, ?, ?, ?, ?, 1)
                    """, (
                        orig,
                        entry.substitute.lower().strip(),
                        entry.ratio,
                        entry.confidence,
                        ",".join(entry.use_cases) if entry.use_cases else "general",
                        entry.reason,
                        entry.notes,
                        entry.source,
                    ))

                # Seed Functional Multi-Ingredient Combinations
                combinations = [
                    (
                        "baking powder",
                        json.dumps(["baking soda", "acidic_agent"]),
                        json.dumps(["plain greek yogurt", "lemon juice", "white vinegar", "cream of tartar", "buttermilk"]),
                        "1/4 tsp baking soda + 1/2 cup yogurt (or 1/2 tsp vinegar/lemon juice) per 1 tsp baking powder",
                        "Baking soda (sodium bicarbonate) combined with an acidic ingredient generates carbon dioxide bubbles to provide vital leavening lift.",
                        json.dumps(["vegetarian", "vegan"]),
                        json.dumps([]),
                        "baking",
                    ),
                    (
                        "buttermilk",
                        json.dumps(["milk", "acidic_agent"]),
                        json.dumps(["lemon juice", "white vinegar", "cream of tartar"]),
                        "1 cup milk + 1 tbsp lemon juice or vinegar",
                        "Acidifying milk curdles proteins and reproduces buttermilk's characteristic tart acidity and chemical leavening reactivity.",
                        json.dumps(["vegetarian"]),
                        json.dumps(["dairy"]),
                        "baking,pancakes",
                    ),
                    (
                        "heavy cream",
                        json.dumps(["milk", "butter"]),
                        json.dumps([]),
                        "3/4 cup milk + 1/4 cup melted butter",
                        "Whisking melted butter into milk reconstructs the high butterfat percentage required for sauces and casseroles.",
                        json.dumps(["vegetarian"]),
                        json.dumps(["dairy"]),
                        "cooking,sauces",
                    ),
                    (
                        "sour cream",
                        json.dumps(["silken tofu", "lemon juice"]),
                        json.dumps([]),
                        "1 cup silken tofu + 1 tbsp lemon juice",
                        "Pureed silken tofu blended with citrus acid replicates creamy mouthfeel and cultured tang without dairy.",
                        json.dumps(["vegetarian", "vegan"]),
                        json.dumps(["soy"]),
                        "cooking,dips",
                    ),
                ]

                cursor.executemany("""
                INSERT OR REPLACE INTO functional_combinations
                (target_ingredient, component_ingredients, acidic_options, ratio, reason, dietary_compatibility, allergens, context)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, combinations)

                conn.commit()

    def _load_from_sqlite(self):
        """Loads all nodes and relational edges from SQLite into NetworkX MultiDiGraph."""
        self.graph.clear()
        self.functional_combinations.clear()

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Load Nodes
            cursor.execute("SELECT * FROM ingredient_nodes")
            for row in cursor.fetchall():
                name = row["canonical_name"]
                self.graph.add_node(
                    name,
                    canonical_name=name,
                    aliases=json.loads(row["aliases"] or "[]"),
                    category=row["category"] or "general",
                    flavor_profile=row["flavor_profile"] or "general",
                    texture=row["texture"] or "general",
                    cooking_role=row["cooking_role"] or "culinary",
                    acidity=row["acidity"] or 0.0,
                    fat_content=row["fat_content"] or 0.0,
                    protein_content=row["protein_content"] or 0.0,
                    dietary_compatibility=json.loads(row["dietary_compatibility"] or "[]"),
                    allergens=json.loads(row["allergens"] or "[]"),
                    cuisine_compatibility=json.loads(row["cuisine_compatibility"] or "[]"),
                )

            # Load Relationships
            cursor.execute("SELECT * FROM ingredient_relationships")
            for row in cursor.fetchall():
                src = row["source_ingredient"].lower().strip()
                tgt = row["target_ingredient"].lower().strip()

                # Ensure source and target nodes exist in graph
                if not self.graph.has_node(src):
                    self.graph.add_node(src, canonical_name=src, category="general", flavor_profile="general", texture="general", cooking_role="culinary", allergens=[], dietary_compatibility=["vegetarian", "vegan"])
                if not self.graph.has_node(tgt):
                    self.graph.add_node(tgt, canonical_name=tgt, category="general", flavor_profile="general", texture="general", cooking_role="culinary", allergens=[], dietary_compatibility=["vegetarian", "vegan"])

                self.graph.add_edge(
                    src,
                    tgt,
                    key=row["relationship_type"],
                    relation_type=row["relationship_type"],
                    ratio=row["ratio"],
                    confidence=row["confidence"] or "medium",
                    context=row["context"] or "general",
                    reason=row["reason"] or "",
                    notes=row["notes"] or "",
                    source=row["source"] or "Culinary Reference Standards",
                    is_verified=bool(row["is_verified"]),
                )

            # Load Functional Combinations
            cursor.execute("SELECT * FROM functional_combinations")
            for row in cursor.fetchall():
                target = row["target_ingredient"].lower().strip()
                self.functional_combinations[target] = {
                    "components": json.loads(row["component_ingredients"] or "[]"),
                    "acidic_options": json.loads(row["acidic_options"] or "[]"),
                    "ratio": row["ratio"],
                    "reason": row["reason"],
                    "dietary": json.loads(row["dietary_compatibility"] or "[]"),
                    "allergens": json.loads(row["allergens"] or "[]"),
                    "context": row["context"] or "general",
                }

        # Automatically construct implicit semantic similarity edges (SAME_COOKING_ROLE, SIMILAR_TEXTURE)
        self._construct_attribute_edges()
        logger.info(f"Loaded Dynamic Substitution Graph: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")

    def _construct_attribute_edges(self):
        """Constructs attribute similarity edges among graph nodes."""
        nodes = list(self.graph.nodes(data=True))
        for i in range(len(nodes)):
            u, d1 = nodes[i]
            role1 = d1.get("cooking_role")
            tex1 = d1.get("texture")
            for j in range(i + 1, len(nodes)):
                v, d2 = nodes[j]
                role2 = d2.get("cooking_role")
                tex2 = d2.get("texture")

                if role1 and role2 and role1 == role2 and role1 != "culinary":
                    self.graph.add_edge(u, v, key="SAME_COOKING_ROLE", relation_type="SAME_COOKING_ROLE", confidence="medium")
                    self.graph.add_edge(v, u, key="SAME_COOKING_ROLE", relation_type="SAME_COOKING_ROLE", confidence="medium")

                if tex1 and tex2 and tex1 == tex2 and tex1 != "general":
                    self.graph.add_edge(u, v, key="SIMILAR_TEXTURE", relation_type="SIMILAR_TEXTURE", confidence="medium")
                    self.graph.add_edge(v, u, key="SIMILAR_TEXTURE", relation_type="SIMILAR_TEXTURE", confidence="medium")

    def _build_in_memory_fallback(self):
        """Fallback graph initialization if SQLite is inaccessible."""
        for node in DEFAULT_INGREDIENT_NODES:
            self.graph.add_node(node["canonical_name"], **node)

    def _resolve_graph_node(self, ingredient_name: str) -> Optional[str]:
        """Resolves any raw ingredient token to an existing node in the NetworkX graph."""
        if not ingredient_name:
            return None

        clean_lower = ingredient_name.lower().strip()
        canonical = resolve_canonical_ingredient(ingredient_name)

        # 1. Direct match
        if self.graph.has_node(clean_lower):
            return clean_lower
        if self.graph.has_node(canonical):
            return canonical

        # 2. Check aliases attribute on graph nodes
        for node, data in self.graph.nodes(data=True):
            aliases = [a.lower().strip() for a in data.get("aliases", [])]
            if clean_lower in aliases or canonical in aliases:
                return node
            for a in aliases:
                if a in clean_lower or clean_lower in a:
                    return node

        # 3. Trailing singularization check
        if clean_lower.endswith("s") and self.graph.has_node(clean_lower[:-1]):
            return clean_lower[:-1]
        if canonical.endswith("s") and self.graph.has_node(canonical[:-1]):
            return canonical[:-1]

        # 4. Substring containment check
        for node in self.graph.nodes:
            if node in clean_lower or clean_lower in node:
                return node

        return None

    def evaluate_safety(
        self,
        candidate_name: str,
        user_diet: Optional[str] = None,
        user_allergens: Optional[List[str]] = None,
    ) -> Tuple[bool, str]:
        """
        Deterministic Allergen & Dietary Hard-Lock Verification.
        Guarantees safety restrictions can NEVER be overridden by similarity scores.
        Returns: (is_safe: bool, reason: str)
        """
        cand_lower = candidate_name.lower().strip()

        # 1. Allergen Hard-Lock
        if user_allergens:
            user_algs_clean = [a.lower().strip() for a in user_allergens]

            # If node exists, inspect node's declared allergen list
            if self.graph.has_node(cand_lower):
                node_algs = [a.lower().strip() for a in self.graph.nodes[cand_lower].get("allergens", [])]
                for alg in user_algs_clean:
                    if alg in node_algs:
                        return False, f"Contains allergen '{alg}'"

            # Check allergen taxonomy keywords against candidate string
            plant_milk_cheese = ["soy milk", "almond milk", "oat milk", "coconut milk", "plant-based", "vegan", "cashew"]
            for alg in user_algs_clean:
                if alg == "dairy" and any(p in cand_lower for p in plant_milk_cheese):
                    continue
                keywords = ALLERGEN_TAXONOMY.get(alg, [alg])
                for kw in keywords:
                    if kw in cand_lower:
                        return False, f"Contains allergen '{alg}' keyword '{kw}'"

        # 2. Dietary Preference Hard-Lock
        if user_diet:
            diet = user_diet.lower().strip()
            if self.graph.has_node(cand_lower):
                node_diets = [d.lower().strip() for d in self.graph.nodes[cand_lower].get("dietary_compatibility", [])]
                if diet == "vegan" and "vegan" not in node_diets:
                    return False, "Not compatible with vegan diet"
                if diet == "vegetarian" and "vegetarian" not in node_diets and "vegan" not in node_diets:
                    return False, "Not compatible with vegetarian diet"

            if diet == "vegan":
                non_vegan = ["milk", "butter", "cheese", "cream", "yogurt", "egg", "eggs", "honey", "pork", "beef", "chicken", "meat", "pepperoni", "salami"]
                plant_safe = ["soy milk", "almond milk", "oat milk", "coconut milk", "vegan", "plant-based", "flax egg", "applesauce"]
                if not any(ps in cand_lower for ps in plant_safe):
                    if any(nv in cand_lower for nv in non_vegan):
                        return False, f"Animal-derived ingredient violating vegan preference"

            if diet == "vegetarian":
                meat_kws = ["beef", "pork", "chicken", "turkey", "bacon", "pepperoni", "salami", "sausage", "ham", "prosciutto", "anchovy", "fish", "meat", "poultry"]
                veg_safe = ["vegan", "plant-based", "tofu", "tempeh"]
                if not any(vs in cand_lower for vs in veg_safe):
                    if any(m in cand_lower for m in meat_kws):
                        return False, f"Meat product violating vegetarian preference"

        return True, "SAFE"

    def calculate_candidate_score(
        self,
        orig_node: Optional[str],
        cand_name: str,
        context: str = "general",
        in_pantry: bool = False,
        is_verified_edge: bool = False,
        is_combination: bool = False,
        edge_context: Optional[str] = None,
    ) -> float:
        """
        Quantifies suitability score based on functional role, texture, flavor, context,
        and pantry availability.
        """
        score = 40.0  # Base score

        if is_verified_edge:
            score += 25.0

        if is_combination:
            score += 20.0

        if in_pantry:
            score += 25.0  # Significant bonus for items readily available in pantry

        # Context alignment from edge metadata
        if edge_context and context and context != "general":
            edge_ctx_lower = str(edge_context).lower()
            if context.lower() in edge_ctx_lower:
                score += 35.0  # Dominant bonus for exact culinary context match (e.g. frying vs baking)
            elif "general" in edge_ctx_lower or "cooking" in edge_ctx_lower:
                score += 5.0
            else:
                score -= 15.0  # Context mismatch penalty (e.g. using baking solid fat for high-heat frying)

        if orig_node and self.graph.has_node(orig_node):
            o_attr = self.graph.nodes[orig_node]
            c_node = self._resolve_graph_node(cand_name)
            if c_node and self.graph.has_node(c_node):
                c_attr = self.graph.nodes[c_node]
                # Role similarity
                if o_attr.get("cooking_role") == c_attr.get("cooking_role"):
                    score += 10.0
                # Texture similarity
                if o_attr.get("texture") == c_attr.get("texture"):
                    score += 5.0
                # Flavor similarity
                if o_attr.get("flavor_profile") == c_attr.get("flavor_profile"):
                    score += 5.0

        # Context alignment bonus for specific ingredient types
        cand_lower = cand_name.lower()
        if context == "baking":
            if any(k in cand_lower for k in ["baking", "soda", "yogurt", "flax", "applesauce", "soy milk"]):
                score += 10.0
        elif context in ("frying", "cooking"):
            if any(k in cand_lower for k in ["oil", "olive oil", "canola", "vegetable oil"]):
                score += 10.0

        return min(100.0, max(0.0, score))

    def evaluate_functional_combinations(
        self,
        missing_canonical: str,
        pantry_set: Set[str],
        context: str = "general",
        dietary_preference: Optional[str] = None,
        allergens: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Evaluates multi-ingredient combinations (e.g. baking soda + acid for baking powder).
        Dynamically checks user's available pantry to recommend concrete available pairings.
        """
        results: List[Dict[str, Any]] = []
        if missing_canonical not in self.functional_combinations:
            return results

        combo_spec = self.functional_combinations[missing_canonical]
        components = combo_spec["components"]
        acidic_options = combo_spec.get("acidic_options", [])

        # Special Case: Baking Powder (Baking soda + Acid)
        if missing_canonical == "baking powder":
            has_soda = any("baking soda" in p or "bicarbonate" in p for p in pantry_set)
            
            # Find which acidic options are currently in the user's pantry
            matched_acid: Optional[str] = None
            for acid in acidic_options:
                canonical_acid = resolve_canonical_ingredient(acid)
                if any(acid in p or p in acid or canonical_acid in p for p in pantry_set):
                    matched_acid = acid
                    break

            # If user has yogurt in pantry, prefer yogurt
            if any("yogurt" in p or "curd" in p for p in pantry_set):
                matched_acid = "yogurt"

            # Formulate the combination recommendation
            if matched_acid:
                combo_name = f"baking soda + {matched_acid}"
                is_safe, safety_msg = self.evaluate_safety(combo_name, dietary_preference, allergens)
                if is_safe:
                    both_in_pantry = has_soda
                    ratio_str = f"1/4 tsp baking soda + 1/2 cup {matched_acid} per 1 tsp baking powder (reduce recipe liquid)" if "yogurt" in matched_acid else f"1/4 tsp baking soda + 1/2 tsp {matched_acid} per 1 tsp baking powder"
                    results.append({
                        "substitute": combo_name,
                        "ratio": ratio_str,
                        "confidence": "high",
                        "substitution_type": "combination",
                        "reason": f"Baking soda combined with {matched_acid} provides the necessary chemical reaction (base + acid) to generate carbon dioxide gas for leavening.",
                        "notes": "Mix the baking soda into dry ingredients and the acid into wet ingredients.",
                        "in_pantry": both_in_pantry,
                        "score": 95.0 if both_in_pantry else 80.0,
                    })

            # Always provide standard reliable combination as baseline
            std_combo = "baking soda + cream of tartar or plain yogurt"
            is_safe, _ = self.evaluate_safety(std_combo, dietary_preference, allergens)
            if is_safe and not any(r["substitute"] == std_combo for r in results):
                results.append({
                    "substitute": std_combo,
                    "ratio": "1/4 tsp baking soda + 1/2 tsp cream of tartar (or 1/2 cup yogurt)",
                    "confidence": "high",
                    "substitution_type": "combination",
                    "reason": combo_spec["reason"],
                    "notes": "Standard CIA chemical leavening ratio.",
                    "in_pantry": has_soda and bool(matched_acid),
                    "score": 75.0,
                })

        # Special Case: Buttermilk (Milk + Acid)
        elif missing_canonical == "buttermilk":
            has_milk = any("milk" in p for p in pantry_set)
            matched_acid: Optional[str] = None
            for acid in acidic_options:
                canonical_acid = resolve_canonical_ingredient(acid)
                if any(acid in p or p in acid or canonical_acid in p for p in pantry_set):
                    matched_acid = acid
                    break
            combo_name = f"milk + {matched_acid}" if matched_acid else "milk + lemon juice or vinegar"
            is_safe, _ = self.evaluate_safety(combo_name, dietary_preference, allergens)
            if is_safe:
                both_in_pantry = has_milk and bool(matched_acid)
                results.append({
                    "substitute": combo_name,
                    "ratio": "1 cup milk + 1 tbsp lemon juice or vinegar",
                    "confidence": "high",
                    "substitution_type": "combination",
                    "reason": combo_spec["reason"],
                    "notes": "Let sit 5 minutes until slightly curdled before adding to batter.",
                    "in_pantry": both_in_pantry,
                    "score": 95.0 if both_in_pantry else 85.0,
                })

        # General Combinations (Heavy Cream, Sour Cream)
        else:
            combo_name = " + ".join(components)
            is_safe, _ = self.evaluate_safety(combo_name, dietary_preference, allergens)
            if is_safe:
                all_in_pantry = all(any(c in p or p in c for p in pantry_set) for c in components)
                results.append({
                    "substitute": combo_name,
                    "ratio": combo_spec["ratio"],
                    "confidence": "high",
                    "substitution_type": "combination",
                    "reason": combo_spec["reason"],
                    "notes": "Whisk or blend thoroughly before incorporating into recipe.",
                    "in_pantry": all_in_pantry,
                    "score": 90.0 if all_in_pantry else 75.0,
                })

        return results

    def find_candidates_for_ingredient(
        self,
        missing_ingredient: str,
        pantry_items: Optional[List[str]] = None,
        context: str = "general",
        dietary_preference: Optional[str] = None,
        user_allergens: Optional[List[str]] = None,
        max_candidates: int = 3,
    ) -> List[SubstitutionCandidate]:
        """
        Dynamically searches the knowledge graph for suitable alternatives for a single missing ingredient.
        Checks:
          1. Multi-ingredient functional combinations (e.g. baking powder, buttermilk).
          2. Verified direct SUBSTITUTES edges.
          3. Role-based & attribute graph traversal (SAME_COOKING_ROLE, SIMILAR_TEXTURE).
          4. Deterministic allergen and dietary safety filters.
          5. Pantry-aware scoring bonuses.
        """
        if not missing_ingredient or not missing_ingredient.strip():
            return []

        pantry_list = [p.lower().strip() for p in (pantry_items or [])]
        pantry_set = set(pantry_list)
        for p in pantry_list:
            norm_p = resolve_canonical_ingredient(p)
            pantry_set.add(norm_p)

        canonical = resolve_canonical_ingredient(missing_ingredient)
        graph_node = self._resolve_graph_node(missing_ingredient) or self._resolve_graph_node(canonical)

        evaluated_candidates: List[Dict[str, Any]] = []
        seen_subs: Set[str] = set()

        # ----------------------------------------------------------------------
        # 1. Multi-Ingredient Functional Combinations
        # ----------------------------------------------------------------------
        combos = self.evaluate_functional_combinations(
            missing_canonical=canonical,
            pantry_set=pantry_set,
            context=context,
            dietary_preference=dietary_preference,
            allergens=user_allergens,
        )
        for c in combos:
            if c["substitute"] not in seen_subs:
                seen_subs.add(c["substitute"])
                evaluated_candidates.append(c)

        # ----------------------------------------------------------------------
        # 2. Verified Direct Outgoing Edges
        # ----------------------------------------------------------------------
        if graph_node and self.graph.has_node(graph_node):
            for _, target, edge_data in self.graph.out_edges(graph_node, data=True):
                if edge_data.get("relation_type") == "SUBSTITUTES":
                    cand_name = target
                    if cand_name in seen_subs:
                        continue

                    # Deterministic Safety Verification
                    is_safe, safety_reason = self.evaluate_safety(cand_name, dietary_preference, user_allergens)
                    if not is_safe:
                        logger.info(f"[Safety Hard-Lock] Rejected '{cand_name}' for '{missing_ingredient}': {safety_reason}")
                        continue

                    cand_canonical = resolve_canonical_ingredient(cand_name)
                    in_pantry = (
                        cand_name in pantry_set
                        or cand_canonical in pantry_set
                        or any(cand_name in p or p in cand_name for p in pantry_set)
                    )

                    score = self.calculate_candidate_score(
                        orig_node=graph_node,
                        cand_name=cand_name,
                        context=context,
                        in_pantry=in_pantry,
                        is_verified_edge=True,
                        edge_context=edge_data.get("context"),
                    )

                    seen_subs.add(cand_name)
                    evaluated_candidates.append({
                        "substitute": cand_name,
                        "ratio": edge_data.get("ratio", "1:1"),
                        "confidence": edge_data.get("confidence", "high"),
                        "substitution_type": edge_data.get("substitution_type", "direct"),
                        "reason": edge_data.get("reason", "Provides equivalent culinary properties."),
                        "notes": edge_data.get("notes", ""),
                        "source": edge_data.get("source", "Culinary Reference Standards"),
                        "in_pantry": in_pantry,
                        "score": score,
                    })

        # ----------------------------------------------------------------------
        # 3. Dynamic Graph Traversal via Functional Role & Texture Neighbors
        # (Evaluates candidates when missing ingredient is unindexed or for ranking)
        # ----------------------------------------------------------------------
        if graph_node and self.graph.has_node(graph_node):
            node_attrs = self.graph.nodes[graph_node]
            target_role = node_attrs.get("cooking_role")

            # Traverse neighbors sharing SAME_COOKING_ROLE
            for u, v, edge_data in self.graph.out_edges(graph_node, data=True):
                if edge_data.get("relation_type") == "SAME_COOKING_ROLE":
                    cand_name = v
                    if cand_name in seen_subs or cand_name == graph_node or cand_name == canonical:
                        continue

                    is_safe, safety_reason = self.evaluate_safety(cand_name, dietary_preference, user_allergens)
                    if not is_safe:
                        continue

                    cand_canonical = resolve_canonical_ingredient(cand_name)
                    in_pantry = (
                        cand_name in pantry_set
                        or cand_canonical in pantry_set
                        or any(cand_name in p or p in cand_name for p in pantry_set)
                    )

                    score = self.calculate_candidate_score(
                        orig_node=graph_node,
                        cand_name=cand_name,
                        context=context,
                        in_pantry=in_pantry,
                        is_verified_edge=False,
                    )

                    seen_subs.add(cand_name)
                    evaluated_candidates.append({
                        "substitute": cand_name,
                        "ratio": "1:1",
                        "confidence": "medium",
                        "substitution_type": "functional",
                        "reason": f"Shares identical '{target_role}' cooking role, providing functional culinary equivalence.",
                        "notes": "Adjust seasoning or liquids to match recipe consistency.",
                        "source": "Dynamic Graph Traversal",
                        "in_pantry": in_pantry,
                        "score": score,
                    })

        # Special Role Check: Egg in Baking
        if canonical == "egg" or "egg" in missing_ingredient.lower():
            # In baking, evaluate yogurt, applesauce, flax egg if in pantry or suitable
            egg_candidates = [
                ("plain greek yogurt", "1/4 cup per egg", "Yogurt provides essential protein and moisture binding without altering batter rise.", "dairy"),
                ("applesauce", "1/4 cup per egg", "Applesauce provides moisture and natural pectin binder for cakes and quick breads.", ""),
                ("flax egg", "1 tbsp flaxseed meal + 3 tbsp water", "Hydrated flaxseed forms a gelatinous binder replicating egg structure in vegan baking.", ""),
                ("mashed banana", "1/2 banana per egg", "Mashed banana binds dry ingredients and adds moisture with a delicate sweetness.", ""),
            ]
            for e_sub, e_ratio, e_reason, e_alg in egg_candidates:
                if e_sub in seen_subs:
                    continue
                is_safe, _ = self.evaluate_safety(e_sub, dietary_preference, user_allergens)
                if not is_safe:
                    continue

                in_pantry = any(e_sub in p or p in e_sub or (e_sub == "plain greek yogurt" and ("yogurt" in p or "curd" in p)) for p in pantry_set)
                score = 85.0 if in_pantry else 70.0
                seen_subs.add(e_sub)
                evaluated_candidates.append({
                    "substitute": e_sub,
                    "ratio": e_ratio,
                    "confidence": "medium" if in_pantry else "medium",
                    "substitution_type": "functional",
                    "reason": e_reason,
                    "notes": "Best suited for pancakes, muffins, and quick breads.",
                    "source": "Culinary Baking Standards",
                    "in_pantry": in_pantry,
                    "score": score,
                })

        # ----------------------------------------------------------------------
        # 4. Fallback Taxonomy Matching for Unindexed / Novel Ingredients
        # ----------------------------------------------------------------------
        if not evaluated_candidates:
            from backend.app.substitutions.taxonomy import match_culinary_taxonomy
            tax_class = match_culinary_taxonomy(missing_ingredient) or match_culinary_taxonomy(canonical)
            if tax_class:
                for default_sub in tax_class.default_substitutes:
                    sub_name = default_sub["substitute"]
                    is_safe, _ = self.evaluate_safety(sub_name, dietary_preference, user_allergens)
                    if not is_safe:
                        continue

                    in_pantry = any(c.strip() in pantry_set for c in sub_name.split(" or "))
                    score = 65.0 + (25.0 if in_pantry else 0.0)

                    evaluated_candidates.append({
                        "substitute": sub_name,
                        "ratio": default_sub["ratio"],
                        "confidence": default_sub["confidence"],
                        "substitution_type": default_sub.get("type", "functional"),
                        "reason": default_sub["reason"],
                        "notes": default_sub.get("notes", ""),
                        "source": "Taxonomy Graph Fallback",
                        "in_pantry": in_pantry,
                        "score": score,
                    })

        # ----------------------------------------------------------------------
        # 5. Sort by Contextual Score & Format into SubstitutionCandidate
        # ----------------------------------------------------------------------
        # Prioritize candidates available in pantry, then higher confidence/score
        evaluated_candidates.sort(key=lambda x: (x.get("in_pantry", False), x.get("score", 0.0)), reverse=True)

        final_candidates: List[SubstitutionCandidate] = []
        for cand in evaluated_candidates[:max_candidates]:
            pantry_note = " (Available in your pantry!)" if cand.get("in_pantry") else ""
            sub_type = cand.get("substitution_type", "direct")
            if any(k in cand["substitute"].lower() for k in [" + ", " with ", " and "]):
                sub_type = "combination"
            final_candidates.append(
                SubstitutionCandidate(
                    missing_ingredient=missing_ingredient,
                    substitute=cand["substitute"],
                    ratio=cand.get("ratio"),
                    confidence=cand.get("confidence", "medium"),
                    substitution_type=sub_type,
                    reason=f"{cand['reason']}{pantry_note}",
                    use_case=context,
                    dietary_compatible=True,
                    safety_status="SAFE",
                    notes=cand.get("notes"),
                    source=cand.get("source", "Dynamic Smart Substitution Graph"),
                    can_omit=False,
                    shopping_suggestion=None if cand.get("in_pantry") else f"Add {cand['substitute']} or {missing_ingredient} to shopping list.",
                )
            )

        return final_candidates

    def find_substitutes(
        self,
        missing_ingredient: str,
        pantry_items: Optional[List[str]] = None,
        context: str = "general",
        dietary_preference: Optional[str] = None,
        user_allergens: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Backwards-compatible API adapter returning candidate dictionary for API endpoints.
        """
        candidates = self.find_candidates_for_ingredient(
            missing_ingredient=missing_ingredient,
            pantry_items=pantry_items,
            context=context,
            dietary_preference=dietary_preference,
            user_allergens=user_allergens,
            max_candidates=5,
        )
        return {
            "missing_ingredient": missing_ingredient,
            "canonical": resolve_canonical_ingredient(missing_ingredient),
            "candidates": [
                {
                    "substitute": c.substitute,
                    "ratio": c.ratio,
                    "confidence": c.confidence,
                    "substitution_type": c.substitution_type,
                    "reason": c.reason,
                    "notes": c.notes,
                    "source": c.source,
                    "safety_status": c.safety_status,
                }
                for c in candidates
            ],
        }


# Singleton instance
substitution_graph = IngredientSubstitutionGraph()
