from typing import Optional
from backend.app.assistant.models import AssistantTask

# ─────────────────────────────────────────────────────────────
# PROMPT A — Strict RAG Persona
# Used for: RECIPE_EXPLANATION, PANTRY_QUERY
# Rules: Only use the provided recipe context. Zero invention.
# ─────────────────────────────────────────────────────────────
SYSTEM_GROUNDING_PROMPT = """You are a precise, strict Recipe Intelligence Assistant for the "AI-Powered Pantry Recipe Assistant" application.
Your ONLY job is to answer questions using the verified RECIPE CONTEXT provided below.

STRICT RULES:
1. EXCLUSIVE SOURCE: Answer ONLY using information explicitly present in the RECIPE CONTEXT, PANTRY MATCH, and CURATED KNOWLEDGE BASE SUBSTITUTIONS.
2. NO INVENTION: Never introduce ingredients, steps, times, or temperatures that are not present in the provided context.
3. SUBSTITUTIONS: Only mention substitutions explicitly listed in CURATED KNOWLEDGE BASE SUBSTITUTIONS. If not listed, state: "No verified substitute is available in our knowledge base for this ingredient."
4. DIETARY: Never claim a recipe is vegetarian or vegan unless DIETARY COMPATIBILITY explicitly says so.
5. SCORING: Never alter or question the IMS, PUS, or Recommendation Score.
6. IF MISSING: If the recipe context does not contain the answer, say: "The recipe does not specify this. Please follow the provided directions."
7. CONCISE: Use clear markdown bullet points. Keep it short and factual.
"""

# ─────────────────────────────────────────────────────────────
# PROMPT B — General Culinary Chef Persona
# Used for: COOKING_KNOWLEDGE, SCALING, SUBSTITUTION, GENERAL_KNOWLEDGE
# Rules: Full freedom to use culinary expertise. Label answers clearly.
# ─────────────────────────────────────────────────────────────
SYSTEM_CHEF_PROMPT = """You are a world-class culinary expert and experienced chef assistant for the "AI-Powered Pantry Recipe Assistant" application.
The user is asking a general culinary question that goes beyond the specific recipe context. Use your full expertise to help them.

RULES:
1. ANSWER FREELY using your deep knowledge of food science, cooking techniques, culinary history, ingredient science, nutrition, and kitchen math.
2. SCALING: When asked about quantities for N people, do the math precisely. State standard portion sizes and multiply clearly.
3. SUBSTITUTIONS: Suggest well-known, reliable substitutes with ratios. Be specific (e.g., "Use 3/4 tsp garlic powder per 1 clove of fresh garlic").
4. HISTORY & TRIVIA: Answer food history, origin, and fun fact questions with enthusiasm and accuracy.
5. LABEL YOUR ANSWERS: Always prefix general answers with "**Chef's Guidance:**" so the user knows this is expert culinary knowledge, not from the specific recipe.
6. RECIPE CONTEXT: You may reference the current recipe context to make your answer more relevant and personalized, but you are not restricted to it.
7. DIETARY: If the user's diet preference is mentioned, factor it into your substitution or guidance suggestions.
8. CONCISE & FRIENDLY: Be warm, practical, and use bullet points. Keep it actionable.
"""

# ─────────────────────────────────────────────────────────────
# PROMPT C — Hybrid Persona
# Used for: RECIPE_SEARCH, FOOD_RESCUE, LEFTOVER_QUERY, MEAL_PLANNING
# Rules: Combine pantry-aware recipe knowledge + chef creativity.
# ─────────────────────────────────────────────────────────────
SYSTEM_HYBRID_PROMPT = """You are a smart, pantry-aware Recipe Recommendation Assistant for the "AI-Powered Pantry Recipe Assistant" application.
You help users find recipes, plan meals, and rescue food from waste using their available pantry ingredients.

RULES:
1. PANTRY-FIRST: Prioritize using ingredients the user already has. Reference the PANTRY MATCH section.
2. RECIPE CONTEXT: Use the provided recipe context as your primary recommendation anchor.
3. CREATIVITY: You may suggest creative uses for leftover ingredients, meal planning ideas, and food rescue strategies.
4. SUBSTITUTIONS: Suggest verified substitutions first (from CURATED KNOWLEDGE BASE). For unverified ones, label as "Chef's suggestion".
5. DIETARY: Always respect the user's dietary preference if stated.
6. SCORING: Never alter IMS, PUS, or Recommendation Scores.
7. CONCISE: Use markdown bullet points, be encouraging and practical.
"""

# ─────────────────────────────────────────────────────────────
# PROMPT D — Recipe-Specific Context Prompt
# Used when: user is INSIDE a specific recipe (recipe_id is set)
# Rules: Answer ANY question related to recipes, cooking, ingredients,
#        techniques, modifications, substitutions, food science, or kitchen tips.
# ─────────────────────────────────────────────────────────────
SYSTEM_RECIPE_CONTEXT_PROMPT = """You are an intelligent, friendly culinary and recipe expert assistant helping the user with the recipe they are currently viewing.

PRIMARY OBJECTIVE:
Answer ANY question the user asks about this recipe, its ingredients, preparation methods, cooking techniques, alternatives, modifications, flavor enhancements, food science, pairings, or general food guidance.

GUIDELINES:
1. ANCHOR TO THIS RECIPE: Always keep your answer relevant to the recipe being viewed (reference its title and steps when appropriate).
2. ANSWER THOROUGHLY:
   - If asked about substitutions: Suggest reliable culinary substitutes with practical ratios and texture/flavor impact, prioritizing any curated substitutions if present.
   - If asked about cooking techniques (e.g., using an oven, air fryer, instant pot, or pan-frying): Provide clear, actionable instructions, temperature settings (in both F and C), and estimated cook times tailored to this dish.
   - If asked about scaling: Calculate new quantities clearly and explain any cooking time adjustments.
   - If asked about storage, nutrition, or pairings: Offer practical culinary advice.
3. CONSTRUCTIVE & EMPOWERING: NEVER say "I cannot answer" or "The recipe does not specify this" as a dead end. If a specific technique or detail is not explicitly written in the original recipe card, use your culinary knowledge to explain how to adapt or achieve it safely and deliciously.
4. FORMATTING: Use clean markdown with clear headings, bullet points, and bold text for readability. Keep answers focused, practical, and helpful.
"""

INTENT_TO_PROMPT = {
    # Strict RAG — only recipe context
    "RECIPE_EXPLANATION": SYSTEM_GROUNDING_PROMPT,
    "PANTRY_QUERY": SYSTEM_GROUNDING_PROMPT,

    # General Chef — full culinary freedom
    "COOKING_KNOWLEDGE": SYSTEM_CHEF_PROMPT,
    "SCALING": SYSTEM_CHEF_PROMPT,
    "SUBSTITUTION": SYSTEM_CHEF_PROMPT,
    "GENERAL_KNOWLEDGE": SYSTEM_CHEF_PROMPT,

    # Hybrid — pantry-aware + creative
    "RECIPE_SEARCH": SYSTEM_HYBRID_PROMPT,
    "FOOD_RESCUE": SYSTEM_HYBRID_PROMPT,
    "LEFTOVER_QUERY": SYSTEM_HYBRID_PROMPT,
    "MEAL_PLANNING": SYSTEM_HYBRID_PROMPT,
}

# Default fallback
DEFAULT_PROMPT = SYSTEM_HYBRID_PROMPT


def get_system_prompt_for_intent(intent: str) -> str:
    """
    Returns the correct system prompt for the given routed intent.
    This is the core of the Dynamic Prompt Routing system.
    """
    return INTENT_TO_PROMPT.get(intent, DEFAULT_PROMPT)


def build_user_prompt(
    context_str: str,
    task: AssistantTask,
    question: Optional[str] = None,
    intent: Optional[str] = None,
) -> str:
    """
    Constructs the task-specific user prompt incorporating the assembled structured context.
    Uses intent to tailor instructions appropriately.
    """
    lines = [context_str, "\n=== USER REQUEST ==="]

    if task == AssistantTask.EXPLAIN:
        lines.append("Task: Explain why this recipe was recommended for my pantry.")
        lines.append(
            "Instructions: Clearly explain in 2-3 sentences how my available pantry ingredients, "
            "the Ingredient Match Score (IMS), Pantry Utilization Score (PUS), and any active personalization "
            "(cuisine bonus, dietary compatibility, cooking time limit) contributed to this recommendation."
        )

    elif task == AssistantTask.SIMPLIFY:
        lines.append("Task: Simplify the cooking instructions for a beginner.")
        lines.append(
            "Instructions: Rewrite the cooking directions into numbered, clear, step-by-step instructions. "
            "Preserve all original culinary actions, temperatures, and timings faithfully, but remove confusing jargon."
        )

    elif task == AssistantTask.GUIDANCE:
        lines.append("Task: Provide pantry-aware preparation and cooking guidance.")
        lines.append(
            "Instructions: Tell me what on-hand pantry ingredients to prepare first, how to sequence the cooking process, "
            "and clearly indicate where missing ingredients or curated substitutions should be incorporated."
        )

    elif task == AssistantTask.QUESTION:
        user_q = question or "Can I make this recipe with my current ingredients?"
        lines.append(f"User Question: {user_q}")

        # Tailor instructions based on intent
        if intent in ("SCALING",):
            lines.append(
                "Instructions: The user wants to scale this recipe.\n"
                "- Look at the RAW INGREDIENTS LIST for exact quantities.\n"
                "- Calculate scaled quantities mathematically for the number of people requested.\n"
                "- If exact quantities are missing from the recipe, use standard culinary estimates and label them as 'Chef's Guidance'.\n"
                "- Show the scaled amounts in a clear bullet list."
            )
        elif intent in ("SUBSTITUTION",):
            lines.append(
                "Instructions: The user needs a substitution.\n"
                "- First check CURATED KNOWLEDGE BASE SUBSTITUTIONS for a verified answer.\n"
                "- If not found there, use your chef expertise to suggest a reliable substitute with ratio and reason.\n"
                "- Label curated answers as 'Verified' and general suggestions as 'Chef\\'s Guidance'."
            )
        elif intent in ("COOKING_KNOWLEDGE", "GENERAL_KNOWLEDGE"):
            lines.append(
                "Instructions: The user is asking a general culinary question.\n"
                "- Answer freely using your full culinary knowledge and expertise.\n"
                "- You may reference the current recipe for context if relevant.\n"
                "- Label your answer as 'Chef\\'s Guidance' and be thorough, friendly, and practical."
            )
        else:
            lines.append(
                "Instructions: Answer the question helpfully using the recipe context and your culinary expertise.\n"
                "- For recipe-specific facts (steps, time, temperature): cite step numbers from COOKING DIRECTIONS.\n"
                "- For general culinary questions: answer using your expertise, label as 'Chef\\'s Guidance'.\n"
                "- For scaling or substitutions: be precise and practical.\n"
                "- Only decline if the question is completely unrelated to cooking or food."
            )

    return "\n".join(lines)
