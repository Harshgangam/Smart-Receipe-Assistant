import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class KnowledgeDocument(BaseModel):
    id: str
    category: str  # "substitution_rules", "storage_guidance", "leftover_transforms", "cooking_technique"
    title: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class VerificationResult(BaseModel):
    is_verified: bool
    refusal_reason: Optional[str] = None
    pantry_compliance_pct: float = 100.0
    dietary_compliant: bool = True
    time_compliant: bool = True
    claims_verified: List[str] = Field(default_factory=list)


class RAGKnowledgeBase:
    """
    Curated RAG Knowledge Base containing verified culinary, storage, substitution,
    technique, and leftover transformation intelligence.
    """

    def __init__(self):
        self.documents: List[KnowledgeDocument] = []
        self._seed_knowledge_base()

    def _seed_knowledge_base(self):
        docs = [
            KnowledgeDocument(
                id="kb_sub_1",
                category="substitution_rules",
                title="Paneer Substitutions",
                content="Paneer can be substituted with Extra-Firm Tofu (ratio 1:1) for vegan options, or Halloumi/Feta for frying.",
                metadata={"role": "protein", "dietary": ["vegan", "vegetarian"]}
            ),
            KnowledgeDocument(
                id="kb_sub_2",
                category="substitution_rules",
                title="Egg Substitutions in Baking",
                content="For baking, 1 egg can be substituted with 1 tbsp chia/flaxseed meal mixed with 3 tbsp water or 1/4 cup unsweetened applesauce.",
                metadata={"role": "binder", "dietary": ["vegan"]}
            ),
            KnowledgeDocument(
                id="kb_sub_3",
                category="substitution_rules",
                title="Onion Substitutions",
                content="If onions are unavailable, substitute with shallots, leeks, green onion / scallions, or 1/4 tsp asafoetida (hing) in Indian cooking.",
                metadata={"role": "aromatic", "ingredient": "onion"}
            ),
            KnowledgeDocument(
                id="kb_sub_banana",
                category="substitution_rules",
                title="Banana Substitutions in Baking & Desserts",
                content="Bananas can be substituted with: ripe plantains (1:1, identical starch and texture), applesauce or mango puree (1:1, 1/2 cup puree per mashed banana, adds natural pectin and sweetness), or steamed sweet potato puree for pies and puddings.",
                metadata={"ingredient": "banana", "role": "sweetener_binder", "dietary": ["vegan", "vegetarian"]}
            ),
            KnowledgeDocument(
                id="kb_storage_1",
                category="storage_guidance",
                title="Spinach Freshness Preservation",
                content="Keep fresh spinach in an airtight container lined with a dry paper towel in the crisper drawer to absorb excess moisture and extend shelf life by 5-7 days.",
                metadata={"ingredient": "spinach", "shelf_extension": "5-7 days"}
            ),
            KnowledgeDocument(
                id="kb_storage_2",
                category="storage_guidance",
                title="Tomato Storage Best Practices",
                content="Store fresh tomatoes at room temperature stem-side down to maintain flavor and texture. Avoid refrigerating uncut tomatoes as cold temperatures degrade cell walls.",
                metadata={"ingredient": "tomatoes", "shelf_extension": "3-5 days"}
            ),
            KnowledgeDocument(
                id="kb_leftover_1",
                category="leftover_transforms",
                title="Leftover Rice Transformation",
                content="Leftover cooked rice stored overnight in the fridge is ideal for Fried Rice or Rice Bowls because the chilled starch grains dry out and do not become mushy.",
                metadata={"ingredient": "rice", "transform_dish": "Fried Rice"}
            ),
            KnowledgeDocument(
                id="kb_leftover_2",
                category="leftover_transforms",
                title="Leftover Curry Wrap / Kathi Roll",
                content="Combine leftover cooked curry with raw sliced red onions, coriander, and fresh lemon juice wrapped in flatbread for a high-value 10-minute rescued lunch.",
                metadata={"ingredient": "curry", "transform_dish": "Kathi Roll"}
            ),
            KnowledgeDocument(
                id="kb_tech_1",
                category="cooking_technique",
                title="Sautéing Technique",
                content="Sautéing is a cooking method that cooks food quickly in a small amount of oil or fat over high heat in a shallow pan, tossing ingredients frequently.",
                metadata={"technique": "sautéing"}
            ),
            KnowledgeDocument(
                id="kb_tech_3",
                category="cooking_technique",
                title="Spiciness Adjustment Technique",
                content="To reduce heat in a dish that is too spicy, add dairy (cream, yogurt, milk, cheese), nut butter, acidic juice (lemon/lime), or a touch of sugar/honey.",
                metadata={"technique": "adjust_spiciness"}
            ),
            KnowledgeDocument(
                id="kb_scaling_1",
                category="serving_scaling",
                title="Rice Serving Size Guide",
                content="Standard serving: 1/4 cup (45g) dry rice per person for a side dish, or 1/3 cup (60g) per person as a main. For 5 people: use 1.25 cups dry rice as a side or ~1.5-2 cups as a main. 1 cup dry rice yields approximately 3 cups cooked rice.",
                metadata={"ingredient": "rice", "type": "scaling"}
            ),
            KnowledgeDocument(
                id="kb_scaling_2",
                category="serving_scaling",
                title="General Ingredient Scaling for More People",
                content="To scale any recipe for more servings, multiply each ingredient quantity by (desired servings / original servings). For example, a recipe for 2 people scaled to 5 people = multiply all quantities by 2.5. Spices and salt should be scaled more conservatively (start at 1.5x and adjust to taste).",
                metadata={"type": "scaling", "technique": "scaling"}
            ),
            KnowledgeDocument(
                id="kb_sub_4",
                category="substitution_rules",
                title="Garlic Substitutions",
                content="Fresh garlic can be substituted with: garlic powder (1/8 tsp per clove), garlic paste (0.5 tsp per clove), or asafoetida/hing (a pinch) in Indian cooking. Roasted garlic can replace raw garlic for a milder, sweeter flavor.",
                metadata={"ingredient": "garlic", "role": "aromatic"}
            ),
            KnowledgeDocument(
                id="kb_sub_5",
                category="substitution_rules",
                title="Tomato Substitutions",
                content="Fresh tomatoes can be substituted with: canned diced tomatoes (3/4 cup per 1 large tomato), tomato paste (1.5 tbsp + 1.5 tbsp water per tomato), or red bell pepper for a milder non-acidic alternative.",
                metadata={"ingredient": "tomato", "role": "base"}
            ),
            KnowledgeDocument(
                id="kb_sub_6",
                category="substitution_rules",
                title="Butter Substitutions",
                content="Butter can be substituted with: equal amount of ghee (richer flavor), coconut oil (for vegan, adds slight sweetness), olive oil (use 3/4 the amount), or vegan butter (1:1 ratio).",
                metadata={"ingredient": "butter", "role": "fat", "dietary": ["vegan"]}
            ),
            KnowledgeDocument(
                id="kb_sub_7",
                category="substitution_rules",
                title="Milk Substitutions",
                content="Regular milk can be substituted with: oat milk, almond milk, soy milk, or coconut milk in a 1:1 ratio. For cooking savory dishes, soy milk or oat milk work best. Coconut milk adds richness but also a slight coconut flavor.",
                metadata={"ingredient": "milk", "role": "liquid", "dietary": ["vegan"]}
            ),
            KnowledgeDocument(
                id="kb_sub_8",
                category="substitution_rules",
                title="Lemon Juice Substitutions",
                content="Lemon juice can be substituted with: equal amount of lime juice, white vinegar (use half the amount), or apple cider vinegar (use half the amount). For zest, use 1/2 tsp dried lemon peel per 1 tsp fresh zest.",
                metadata={"ingredient": "lemon", "role": "acid"}
            ),
            KnowledgeDocument(
                id="kb_sub_9",
                category="substitution_rules",
                title="Flour Substitutions (Whole Wheat, Almond, Oat, Gluten-Free)",
                content="All-purpose flour can be substituted with: Whole Wheat Flour (use 3/4 cup per 1 cup white flour, or 50/50 mix plus 1-2 tbsp extra liquid for moisture), Oat Flour (1:1 ratio for muffins and cookies), Almond Flour (1:1 ratio, baked goods will be denser and richer), or 1:1 Gluten-Free Baking Blend with xanthan gum.",
                metadata={"ingredient": "flour", "role": "structure", "dietary": ["gluten-free", "whole-grain"]}
            ),
            KnowledgeDocument(
                id="kb_sub_10",
                category="substitution_rules",
                title="Sugar and Sweetener Substitutions",
                content="White sugar can be substituted with: brown sugar (1:1, adds moisture and caramel notes), honey or maple syrup (use 3/4 cup per 1 cup sugar and reduce other liquids by 3 tbsp), or coconut sugar (1:1 ratio).",
                metadata={"ingredient": "sugar", "role": "sweetener"}
            ),
            KnowledgeDocument(
                id="kb_sub_11",
                category="substitution_rules",
                title="Baking Powder and Soda Substitutions",
                content="1 tsp baking powder can be substituted with: 1/4 tsp baking soda plus 1/2 tsp cream of tartar (or 1/2 tsp vinegar/lemon juice mixed into liquid ingredients).",
                metadata={"ingredient": "baking powder", "role": "leavening"}
            ),
            KnowledgeDocument(
                id="kb_storage_3",
                category="storage_guidance",
                title="Cooked Rice Storage",
                content="Cooked rice should be cooled within 1 hour and stored in an airtight container in the fridge for up to 4 days. Never leave cooked rice at room temperature for more than 2 hours. Reheat thoroughly before eating.",
                metadata={"ingredient": "rice", "shelf_life": "4 days"}
            ),
        ]
        self.documents = docs

    def retrieve_relevant_docs(self, query: str, top_k: int = 3) -> List[KnowledgeDocument]:
        query_words = set(query.lower().split())
        scored_docs = []

        for doc in self.documents:
            doc_text = f"{doc.title} {doc.content} {' '.join(doc.metadata.values() if isinstance(doc.metadata.values(), list) else [])}".lower()
            doc_words = set(doc_text.split())
            overlap = len(query_words.intersection(doc_words))
            scored_docs.append((overlap, doc))

        scored_docs.sort(key=lambda x: -x[0])
        return [doc for score, doc in scored_docs[:top_k] if score > 0] or self.documents[:top_k]


class RecipeVerifier:
    """
    Recipe Verification Layer checking generated responses against dietary restrictions,
    pantry availability bounds, and cooking time limits.
    """

    @staticmethod
    def verify_recipe_recommendation(
        recipe_title: str,
        recipe_ner: List[str],
        pantry_ingredients: List[str],
        dietary_preference: Optional[str] = None,
        max_cooking_time: Optional[int] = None,
        estimated_time: Optional[int] = None,
        recipe_compatibility: Optional[str] = None,
    ) -> VerificationResult:
        pantry_set = {p.lower().strip() for p in pantry_ingredients}
        recipe_set = {r.lower().strip() for r in recipe_ner}

        matched = sum(1 for ing in recipe_set if any(p in ing or ing in p for p in pantry_set))
        compliance_pct = (matched / len(recipe_set) * 100.0) if recipe_set else 100.0

        dietary_compliant = True
        refusal_reason = None

        if dietary_preference:
            pref = dietary_preference.lower()
            compat = (recipe_compatibility or "non_vegetarian").lower()
            if pref == "vegetarian" and compat not in ("vegetarian_compatible", "vegan_compatible"):
                dietary_compliant = False
                refusal_reason = f"Recipe '{recipe_title}' contains non-vegetarian ingredients violating vegetarian filter."
            elif pref == "vegan" and compat != "vegan_compatible":
                dietary_compliant = False
                refusal_reason = f"Recipe '{recipe_title}' is not fully vegan compatible."

        time_compliant = True
        if max_cooking_time and estimated_time:
            if estimated_time > max_cooking_time:
                time_compliant = False
                refusal_reason = f"Cooking time ({estimated_time}m) exceeds specified limit of {max_cooking_time}m."

        is_verified = dietary_compliant and time_compliant and (compliance_pct >= 30.0)

        claims = [
            f"Pantry Match: {matched}/{len(recipe_set)} ingredients ({round(compliance_pct, 1)}%)",
            f"Dietary Status: {'Verified Compliant' if dietary_compliant else 'Non-Compliant'}",
            f"Cooking Time Status: {'Within Limit' if time_compliant else 'Exceeds Limit'}",
        ]

        return VerificationResult(
            is_verified=is_verified,
            refusal_reason=refusal_reason,
            pantry_compliance_pct=round(compliance_pct, 1),
            dietary_compliant=dietary_compliant,
            time_compliant=time_compliant,
            claims_verified=claims,
        )


# Singleton instances
rag_knowledge_base = RAGKnowledgeBase()
recipe_verifier = RecipeVerifier()
