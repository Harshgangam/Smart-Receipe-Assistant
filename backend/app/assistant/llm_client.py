import logging
import re
from typing import Any, Dict, List, Optional
import httpx

from backend.app.assistant.models import AssistantTask, StructuredRecipeContext
from backend.app.config import settings

logger = logging.getLogger(__name__)


class BaseLLMClient:
    """Abstract interface for LLM client providers."""

    provider_name: str = "base"
    model_name: str = "base-model"
    is_mock: bool = False

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: StructuredRecipeContext,
        task: AssistantTask,
        question: Optional[str] = None,
    ) -> str:
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    """
    Deterministic, rule-grounded fallback LLM client.
    Generates realistic, faithful culinary answers strictly from StructuredRecipeContext.
    Guarantees 100% offline testability, zero API cost, and high reliability.
    """

    provider_name: str = "mock"
    model_name: str = "deterministic-rule-grounded"
    is_mock: bool = True

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: StructuredRecipeContext,
        task: AssistantTask,
        question: Optional[str] = None,
    ) -> str:
        if task == AssistantTask.EXPLAIN:
            return self._explain(context)
        elif task == AssistantTask.SIMPLIFY:
            return self._simplify(context)
        elif task == AssistantTask.GUIDANCE:
            return self._guidance(context)
        else:
            return self._answer_question(context, question or "", user_prompt)

    def _explain(self, context: StructuredRecipeContext) -> str:
        matched_str = ", ".join(context.matched_ingredients) if context.matched_ingredients else "none"
        missing_count = len(context.missing_ingredients)

        cuisine_clause = ""
        if context.cuisine and context.cuisine.lower() == (context.cuisine_preference_applied or "").lower():
            cuisine_clause = f" It matches your preference for {context.cuisine} cuisine."
        elif context.cuisine:
            cuisine_clause = f" It is identified as {context.cuisine} cuisine."

        diet_clause = ""
        if context.dietary_compatibility:
            diet_clause = f" Dietary compatibility is classified as {context.dietary_compatibility.replace('_', ' ')}."

        time_clause = ""
        if context.estimated_time_minutes:
            time_clause = f" It takes an estimated {context.estimated_time_minutes} minutes to cook."

        missing_clause = ""
        if missing_count > 0:
            if context.substitutions:
                missing_clause = f" You only need {missing_count} additional item(s), with verified substitutions available for on-hand alternatives."
            else:
                missing_clause = f" You need {missing_count} additional ingredient(s) from your grocery store."
        else:
            missing_clause = " You have 100% of the required ingredients ready in your pantry!"

        return (
            f"**{context.title}** was recommended because you have **{len(context.matched_ingredients)} of {len(context.ner)}** "
            f"recipe ingredients on hand ({matched_str}), achieving an **Ingredient Match Score (IMS) of {context.ims:.1f}%** "
            f"and a **Pantry Utilization Score (PUS) of {context.pus:.1f}%** (Final Score: {context.recommendation_score:.1f})."
            f"{cuisine_clause}{diet_clause}{time_clause}{missing_clause}"
        )

    def _simplify(self, context: StructuredRecipeContext) -> str:
        lines = [f"Here is the simplified, step-by-step cooking guide for **{context.title}**:"]
        for idx, step in enumerate(context.directions, 1):
            clean_step = step.strip()
            # Clean step of redundant prefix numbers if present
            clean_step = re.sub(r"^\d+[\.\)]\s*", "", clean_step)
            lines.append(f"{idx}. {clean_step}")

        if context.estimated_time_minutes:
            lines.append(f"\n*Estimated active cooking time: ~{context.estimated_time_minutes} minutes.*")
        return "\n".join(lines)

    def _guidance(self, context: StructuredRecipeContext) -> str:
        matched_str = ", ".join(context.matched_ingredients) if context.matched_ingredients else "staple pantry items"
        lines = [
            f"### Pantry-Aware Preparation & Cooking Sequence for *{context.title}*",
            f"1. **Prep on-hand pantry ingredients first**: Set out your **{matched_str}** so they are measured and ready before cooking.",
        ]

        if context.directions:
            first_step = context.directions[0].strip()
            lines.append(f"2. **Initial cooking action**: Follow Step 1 — {first_step}")

        if context.substitutions:
            lines.append("3. **Incorporate verified substitutions**:")
            for sub in context.substitutions:
                ratio_txt = f" using a {sub['ratio']} ratio" if sub.get("ratio") else ""
                lines.append(
                    f"   - Replace missing *{sub['missing_ingredient']}* with **{sub['substitute']}**{ratio_txt} ({sub['reason']})."
                )
        elif context.missing_ingredients:
            missing_str = ", ".join(context.missing_ingredients)
            lines.append(f"3. **Missing components**: Gather {missing_str} before starting.")

        lines.append("4. **Finishing**: Complete according to the remaining recipe steps and serve hot.")
        return "\n".join(lines)

    def _answer_question(self, context: StructuredRecipeContext, question: str, user_prompt: str = "") -> str:
        q_lower = question.lower().strip()
        words = [re.sub(r"[^\w]", "", w) for w in q_lower.split() if w]

        # 0. LEFTOVER / REPURPOSE QUESTIONS — answer using this recipe's ingredients
        leftover_triggers = ["leftover", "left over", "repurpose", "use up", "make a new dish", "use the rest", "remaining"]
        if any(t in q_lower for t in leftover_triggers):
            ner_str = ", ".join(context.ner[:6]) if context.ner else "the ingredients"
            directions_hint = f" The recipe involves: {context.directions[0].strip()[:120]}..." if context.directions else ""
            return (
                f"For leftover ingredients from **{context.title}**, here are some ideas based on this recipe's components ({ner_str}):\n"
                f"- **Transform into a new dish**: The cooked components from this recipe can be repurposed. "
                f"For example, sun-dried or roasted ingredients make excellent pasta toppings, sandwich fillings, or pizza toppings.\n"
                f"- **Store properly**: Keep leftovers in an airtight container in the fridge for up to 3-4 days.\n"
                f"- **Quick remix**: Toss leftover ingredients from this recipe with pasta, rice, or flatbread for a 10-minute rescued meal.\n"
                f"{directions_hint}\n"
                f"*Note: For richer AI-powered suggestions, connect an LLM API key in your `.env` file.*"
            )

        # 0b. SPEED / FASTER COOKING — answer using this recipe's actual steps
        speed_triggers = ["faster", "quickly", "quick", "speed up", "in 10 minutes", "in 15 minutes", "in 20 minutes", "less time", "shortcut"]
        if any(t in q_lower for t in speed_triggers):
            steps_count = len(context.directions)
            time_info = f"{context.estimated_time_minutes} minutes" if context.estimated_time_minutes else "an unspecified amount of time"
            quick_tips = []
            for idx, step in enumerate(context.directions[:4], 1):
                step_l = step.lower()
                if any(kw in step_l for kw in ["preheat", "boil", "heat", "prepare"]):
                    quick_tips.append(f"- **Step {idx}** (do this first in parallel): {step.strip()[:100]}...")
            tips_str = "\n".join(quick_tips) if quick_tips else "- Start prep steps (chopping, preheating) simultaneously to save time."
            return (
                f"To cook **{context.title}** faster (currently estimated at {time_info}, {steps_count} steps):\n"
                f"{tips_str}\n"
                f"- **Parallel prep**: While one step is running (e.g. preheating), prepare ingredients for the next step.\n"
                f"- **Skip resting time**: If the recipe has any resting or cooling steps, you can reduce them slightly.\n"
                f"- **High heat option**: Some steps may tolerate slightly higher heat to reduce cook time — watch carefully.\n"
                f"*Tip: Check the COOKING DIRECTIONS for this recipe's specific steps to identify which ones can overlap.*"
            )

        # 0c. SCALING — answer using this recipe's actual ingredient list
        scaling_triggers = ["for 5 people", "for 4 people", "for 3 people", "for 6 people", "for 2 people",
                            "for 10 people", "scale", "servings", "double", "triple", "half"]
        serving_match = re.search(r"for\s+(\d+)\s+(?:people|persons?|servings?)", q_lower)
        if serving_match or any(t in q_lower for t in scaling_triggers):
            target = int(serving_match.group(1)) if serving_match else 4
            ing_list = "\n".join([f"- {ing}" for ing in context.ingredients[:8]]) if context.ingredients else "- (ingredients not listed with quantities)"
            return (
                f"To scale **{context.title}** for **{target} people**, multiply all ingredient quantities by approximately **{target}/2** "
                f"(assuming the original recipe serves ~2):\n\n"
                f"**Original ingredients (scale each by ×{target/2:.1f}):**\n{ing_list}\n\n"
                f"*General culinary tip: Scale spices and salt more conservatively — start at ×{max(1, target/2 - 0.5):.1f} and adjust to taste.*"
            )

        # 1. SUBSTITUTION INQUIRIES
        is_temp_query = any(k in q_lower for k in ["degrees", "temperature", "oven temp", "bake at", "degrees instead"])
        sub_triggers = [
            "substitute", "substitutes", "substitution", "substitutions",
            "replace", "replacing", "replacement", "swap", "swapping",
            "instead of", "alternative", "without", "omit", "leave out",
            "make this with", "make with", "can i use",
            "what if i don't have", "what if i have no",
            "use whole wheat", "use almond", "use oat", "use gluten"
        ]
        if not is_temp_query and any(t in q_lower for t in sub_triggers):
            # A. Check verified substitutions attached to this context
            for sub in context.substitutions:
                missing_ing = sub["missing_ingredient"].lower()
                sub_ing = sub["substitute"].lower()
                if missing_ing in q_lower or sub_ing in q_lower:
                    ratio_info = f" with a ratio of **{sub['ratio']}**" if sub.get("ratio") else ""
                    return (
                        f"Yes, according to our verified knowledge base, you can substitute **{sub['missing_ingredient']}** "
                        f"with **{sub['substitute']}**{ratio_info} (Confidence: {sub['confidence']}). "
                        f"Reason: {sub['reason']}"
                    )

            # A2. Check entire curated substitution database for matching pair or ingredient
            from backend.app.substitutions.knowledge_base import SUBSTITUTION_DATABASE
            
            # Check for specific candidate pair in query: "Can I substitute X for Y"
            # Here X is proposed substitute, Y is original ingredient.
            pair_match = re.search(r"substitute\s+([a-zA-Z\s]+?)\s+(?:for|instead\s+of)\s+([a-zA-Z\s]+)", q_lower)
            if pair_match:
                proposed_sub = pair_match.group(1).strip()
                orig_ing = pair_match.group(2).strip()
                # Verify if proposed_sub is an approved substitute for orig_ing
                valid_pair = False
                matched_kb = None
                for entry in SUBSTITUTION_DATABASE:
                    if (entry.original_ingredient.lower() in orig_ing or orig_ing in entry.original_ingredient.lower()):
                        matched_kb = entry
                        if proposed_sub in entry.substitute.lower():
                            valid_pair = True
                            break
                if valid_pair and matched_kb:
                    ratio_info = f" with a ratio of **{matched_kb.ratio}**" if matched_kb.ratio else ""
                    return (
                        f"Yes, according to our verified culinary knowledge base, you can substitute **{matched_kb.original_ingredient}** "
                        f"with **{matched_kb.substitute}**{ratio_info} (Confidence: {matched_kb.confidence}). "
                        f"Reason: {matched_kb.reason}"
                    )
                else:
                    return (
                        f"I cannot confirm a reliable culinary substitute of **{proposed_sub}** for **{orig_ing}** based on our verified knowledge base. "
                        f"Substituting it may unpredictably alter the intended texture, moisture, or flavor balance of **{context.title}**."
                    )

            best_entry = None
            best_score = 0
            q_tokens = set(re.findall(r"[a-zA-Z]+", q_lower))
            for entry in SUBSTITUTION_DATABASE:
                orig = entry.original_ingredient.lower()
                sub = entry.substitute.lower()
                orig_tokens = set(re.findall(r"[a-zA-Z]+", orig))
                sub_tokens = set(re.findall(r"[a-zA-Z]+", sub))

                # Exact full phrase match
                if orig in q_lower:
                    score = 20
                elif orig_tokens.issubset(q_tokens):
                    score = 15
                elif sub_tokens.issubset(q_tokens):
                    score = 10
                else:
                    score = 0

                if score > best_score:
                    best_score = score
                    best_entry = entry

            if best_entry and best_score >= 10:
                ratio_info = f" with a ratio of **{best_entry.ratio}**" if best_entry.ratio else ""
                return (
                    f"Yes, according to our verified culinary knowledge base, you can substitute **{best_entry.original_ingredient}** "
                    f"with **{best_entry.substitute}**{ratio_info} (Confidence: {best_entry.confidence}). "
                    f"Reason: {best_entry.reason}"
                )

            # B. Negative constraint: check if an ingredient from NER or raw ingredients is mentioned
            for ing in context.ner:
                if ing.lower() in q_lower:
                    return (
                        f"I cannot confirm a reliable culinary substitute for **{ing}** based on our verified knowledge base. "
                        f"Substituting or omitting it may alter the intended flavor, texture, or chemistry of **{context.title}**."
                    )

            # Check raw ingredients for match (e.g. mushrooms, sausage, etc.)
            for raw in context.ingredients:
                for w in re.findall(r"[a-zA-Z]+", raw.lower()):
                    if len(w) > 3 and w in q_lower and w not in ["package", "packages", "tbsp", "teaspoon", "tablespoon", "clove", "cloves", "large", "small", "fresh", "bake", "cook", "heat"]:
                        return (
                            f"I cannot confirm a reliable culinary substitute for **{w}** based on our verified knowledge base. "
                            f"Substituting or omitting it may alter the intended flavor, texture, or chemistry of **{context.title}**."
                        )

            # C. Generic unverified ingredient check (e.g. "Can I substitute apples for mushrooms?")
            stop_words = {"can", "substitute", "replace", "swap", "instead", "without", "recipe", "make", "this", "with", "for", "using", "use", "dish", "bake", "cook"}
            candidates = [w for w in words if len(w) > 3 and w not in stop_words]
            item_name = candidates[0] if candidates else "this ingredient"
            return (
                f"I cannot confirm a reliable culinary substitute for **{item_name}** based on our verified knowledge base. "
                f"Substituting it may alter the structure or flavor of this recipe."
            )

        # 1b. TEMPERATURE / OVEN INQUIRIES
        if is_temp_query or any(t in q_lower for t in ["temperature", "preheat", "degrees f", "degrees c", "how hot"]):
            # Check directions for specified baking temperature
            temp_match = None
            for step in context.directions:
                found = re.search(r"(\d{3})\s*(?:degrees|[°]|\s*f|\s*degrees\s*f)", step, re.IGNORECASE)
                if found:
                    temp_match = (found.group(1), step)
                    break
            if temp_match:
                return (
                    f"The recipe directions for **{context.title}** call for baking at **{temp_match[0]}°F**:\n"
                    f"- {temp_match[1]}\n\n"
                    f"If you adjust the temperature by 25°F, adjust the cooking time accordingly (lower temperature requires ~5-10 minutes longer; higher temperature bakes faster—check with a toothpick for doneness)."
                )
            return f"The recipe directions and metadata for **{context.title}** do not specify or contain information regarding an oven temperature."

        # 2. TIME / DURATION INQUIRIES
        time_triggers = ["how long", "time", "duration", "minutes", "prep time", "cook time", "cooking time"]
        if any(t in q_lower for t in time_triggers):
            if context.estimated_time_minutes:
                return (
                    f"The estimated active cooking time for **{context.title}** is **{context.estimated_time_minutes} minutes** "
                    f"(Confidence: {context.time_confidence or 'high'})."
                )
            return f"The recipe directions and metadata for **{context.title}** do not specify an exact active cooking duration."

        # 3. PANTRY & INGREDIENT AVAILABILITY INQUIRIES
        missing_triggers = ["missing", "need to buy", "what do i need", "what am i missing", "lacking", "don't have", "do not have", "need to get"]
        if any(t in q_lower for t in missing_triggers):
            if context.missing_ingredients:
                missing_str = ", ".join(context.missing_ingredients)
                sub_note = ""
                if context.substitutions:
                    verified_subs = [f"{s['missing_ingredient']} (substitute with {s['substitute']})" for s in context.substitutions]
                    sub_note = f" Verified substitutions available in our knowledge base: {', '.join(verified_subs)}."
                return f"For **{context.title}**, you are currently missing {len(context.missing_ingredients)} ingredient(s): **{missing_str}**.{sub_note}"
            return f"You have all required ingredients in your pantry for **{context.title}** (100% Ingredient Match Score)!"

        pantry_triggers = ["pantry", "on hand", "already have", "do i have", "available ingredients", "in my pantry", "have on hand"]
        if any(t in q_lower for t in pantry_triggers):
            for ing in context.ner:
                if ing.lower() in q_lower:
                    if ing in context.matched_ingredients:
                        return f"Yes, **{ing}** is available in your pantry and matches the requirements for **{context.title}**."
                    elif ing in context.missing_ingredients:
                        return f"No, **{ing}** is currently missing from your pantry for **{context.title}**."
            matched_str = ", ".join(context.matched_ingredients) if context.matched_ingredients else "none"
            return (
                f"From your pantry, you have **{len(context.matched_ingredients)} of {len(context.ner)}** ingredients "
                f"on hand for **{context.title}** ({context.ims:.1f}% Match Score): **{matched_str}**."
            )

        # 4. CUISINE & DIETARY INQUIRIES
        if any(t in q_lower for t in ["cuisine", "origin", "style"]):
            return f"**{context.title}** is classified as **{context.cuisine or 'Unclassified'}** cuisine (Confidence: {context.cuisine_confidence or 'None'})."

        if any(t in q_lower for t in ["vegan", "vegetarian", "meat", "dairy", "diet", "dietary"]):
            diet = (context.dietary_compatibility or "standard").replace("_", " ")
            return f"Based on ingredient taxonomy, **{context.title}** is classified as **{diet}** (Confidence: {context.dietary_confidence or 'None'})."

        # 5. STEP / DIRECTION / METHOD / PREPARATION SEQUENCE QUESTIONS
        first_step_triggers = ["first step", "step 1", "start", "begin", "initially"]
        if any(t in q_lower for t in first_step_triggers) and context.directions:
            return f"The initial step for **{context.title}** is:\n- **Step 1**: {context.directions[0]}"

        stop_words = {
            "how", "should", "i", "the", "a", "an", "is", "are", "do", "does", "what", "when", "where",
            "why", "to", "in", "on", "for", "with", "of", "and", "can", "please", "would", "could",
            "about", "this", "that", "there", "these", "those", "you", "your", "we", "our", "me", "my",
            "tell", "explain", "describe", "much", "many"
        }
        q_content_words = [w for w in words if w not in stop_words and len(w) > 2]

        # Extract entities mentioned in query from NER, raw ingredients, or directions
        entities = set(context.ner)
        raw_ingredient_words: Dict[str, List[str]] = {}
        for ing in context.ingredients:
            for w in re.findall(r"[a-zA-Z]+", ing.lower()):
                if len(w) > 3 and w not in stop_words:
                    entities.add(w)
                    raw_ingredient_words.setdefault(w, []).append(ing)

        # Also add direction nouns (e.g. "vegetables", "skillet", "drippings")
        for step in context.directions:
            for w in re.findall(r"[a-zA-Z]+", step.lower()):
                if len(w) > 4 and w not in stop_words:
                    entities.add(w)

        matched_entities = [e for e in entities if e in q_lower]

        has_before = "before" in q_lower
        has_after = "after" in q_lower

        anchor_entity = None
        subject_entity = None
        if has_before:
            parts = q_lower.split("before", 1)
            for e in matched_entities:
                if e in parts[1]:
                    anchor_entity = e
                elif e in parts[0]:
                    subject_entity = e
        elif has_after:
            parts = q_lower.split("after", 1)
            for e in matched_entities:
                if e in parts[1]:
                    anchor_entity = e
                elif e in parts[0]:
                    subject_entity = e

        if not subject_entity and matched_entities:
            subject_entity = matched_entities[0]
            if len(matched_entities) > 1 and not anchor_entity:
                anchor_entity = matched_entities[1]

        # Expand related terms for subject entity (e.g. "sausage" -> "links")
        related_subject_terms = {subject_entity} if subject_entity else set()
        if subject_entity and subject_entity in raw_ingredient_words:
            for raw in raw_ingredient_words[subject_entity]:
                for w in re.findall(r"[a-zA-Z]+", raw.lower()):
                    if len(w) > 3 and w not in stop_words:
                        related_subject_terms.add(w)

        # Find steps mentioning anchor entity
        anchor_steps = []
        if anchor_entity:
            for idx, step in enumerate(context.directions, 1):
                if anchor_entity in step.lower():
                    anchor_steps.append(idx)

        # Score direction steps
        scored_steps = []
        target_anchor = None
        if has_before and anchor_steps:
            adding_steps = [s for s in anchor_steps if any(w in context.directions[s-1].lower() for w in ["add", "toss", "mix", "pour", "combine"])]
            target_anchor = adding_steps[0] if adding_steps else anchor_steps[-1]
        elif has_after and anchor_steps:
            target_anchor = min(anchor_steps)

        for idx, step in enumerate(context.directions, 1):
            step_l = step.lower()
            score = 0

            # Subject matching
            for term in related_subject_terms:
                if term in step_l:
                    score += 12

            # Match content words (verbs, nouns)
            for qw in q_content_words:
                if qw in step_l:
                    score += 4

            # Sequence adjustments
            if has_before and target_anchor:
                if idx < target_anchor and score > 0:
                    score += 10
                elif idx == target_anchor:
                    score += 1
                elif idx > target_anchor:
                    score -= 10
            elif has_after and target_anchor:
                if idx > target_anchor and score > 0:
                    score += 10
                elif idx <= target_anchor:
                    score -= 10

            if score > 0:
                scored_steps.append((idx, score, step))

        scored_steps.sort(key=lambda x: (x[1], -x[0]), reverse=True)

        if scored_steps and scored_steps[0][1] >= 8:
            if has_before and target_anchor:
                before_steps = [s for s in scored_steps if s[0] < target_anchor and s[1] >= 8][:4]
                before_steps.sort(key=lambda x: x[0])
                step_lines = [f"- **Step {s[0]}**: {s[2]}" for s in before_steps]
                intro = f"According to the recipe directions for **{context.title}**, here is how to cook and prepare the **{subject_entity or 'ingredient'}** before adding the **{anchor_entity or 'pasta'}**:"
                outro = f"\nFinally, in **Step {target_anchor}**: {context.directions[target_anchor-1]}"
                return intro + "\n" + "\n".join(step_lines) + outro
            else:
                top_steps = [s for s in scored_steps if s[1] >= 8][:4]
                top_steps.sort(key=lambda x: x[0])
                step_lines = [f"- **Step {s[0]}**: {s[2]}" for s in top_steps]
                if subject_entity:
                    intro = f"According to the recipe directions for **{context.title}**, here is how **{subject_entity}** is used and prepared:"
                else:
                    intro = f"Based on the recipe directions for **{context.title}**, the following steps are relevant to your question:"
                return intro + "\n" + "\n".join(step_lines)

        # 5b. RAG KNOWLEDGE BASE FALLBACK — search user prompt for relevant verified knowledge
        if "=== VERIFIED RAG KNOWLEDGE BASE DOCS ===" in user_prompt:
            rag_section = user_prompt.split("=== VERIFIED RAG KNOWLEDGE BASE DOCS ===")[1].split("===")[0].strip()
            rag_lines = [line.strip("- * \t") for line in rag_section.split("\n") if line.strip()]
            for line in rag_lines:
                # Check for word overlap between query and knowledge doc line
                line_lower = line.lower()
                overlap_count = sum(1 for w in words if len(w) > 3 and w in line_lower)
                if overlap_count >= 1:
                    return (
                        f"Based on our verified culinary knowledge base for **{context.title}**:\n\n"
                        f"{line}\n\n"
                        f"*Verified against culinary science and recipe ingredients.*"
                    )

        # 6. CULINARY EXPERT FALLBACK — provide a helpful, practical response tailored to the recipe
        q_cleaned = re.sub(r"[^\w\s]", "", q_lower).strip()
        ner_list = context.ner if context.ner else [re.sub(r"[^\w\s]", "", ing).strip() for ing in context.ingredients]
        steps = [s.strip() for s in context.directions if s.strip()]

        return (
            f"Regarding **{context.title}** and your question (*\"{question}\"*):\n\n"
            f"Here is practical culinary guidance tailored to this dish:\n"
            f"- **Preparation & Technique**: Follow the primary cooking steps ({len(steps)} steps listed). If adapting for an alternative method (like oven baking or air frying), preheat to 375°F (190°C) and monitor closely until golden and cooked through.\n"
            f"- **Core Ingredients**: {', '.join(ner_list[:6])}.\n"
            f"- **Flavor & Seasoning**: Adjust salt, pepper, and aromatics according to taste during the final minutes of cooking.\n"
            f"- **Storage & Leftovers**: Keep in an airtight container refrigerated for up to 3–4 days; reheat thoroughly before serving."
        )



class GeminiClient(BaseLLMClient):
    """Client for Google Gemini API via lightweight HTTP calls."""

    provider_name: str = "gemini"
    is_mock: bool = False

    def __init__(self, api_key: str, model_name: str = "gemini-3.5-flash", temperature: float = 0.2, max_tokens: int = 600):
        self.api_key = api_key
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.fallback = MockLLMClient()

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: StructuredRecipeContext,
        task: AssistantTask,
        question: Optional[str] = None,
    ) -> str:
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{system_prompt}\n\n{user_prompt}"}],
                }
            ],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": max(self.max_tokens, 1500),
            },
        }

        # Prioritize stable, fast models that avoid 503 high-demand errors
        candidate_models = ["gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.6-flash"]
        if self.model_name and self.model_name not in candidate_models:
            candidate_models.insert(0, self.model_name)


        for model in candidate_models:
            clean_model = model.replace("models/", "")
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{clean_model}:generateContent?key={self.api_key}"
            try:
                with httpx.Client(timeout=20.0) as client:
                    response = client.post(url, headers={"Content-Type": "application/json"}, json=payload)
                    if response.status_code == 200:
                        data = response.json()
                        candidates = data.get("candidates", [])
                        if candidates and "content" in candidates[0]:
                            parts = candidates[0]["content"].get("parts", [])
                            if parts and "text" in parts[0]:
                                self.model_name = clean_model
                                return parts[0]["text"].strip()
                    logger.warning(
                        f"Gemini model {clean_model} returned status {response.status_code}: {response.text[:200]}"
                    )
            except Exception as e:
                logger.warning(f"Error calling Gemini model {clean_model}: {e}")

        logger.info("Falling back to deterministic rule-grounded MockLLMClient.")
        return self.fallback.generate(system_prompt, user_prompt, context, task, question)



class OpenAIClient(BaseLLMClient):
    """Client for OpenAI-compatible chat completion APIs (OpenAI, Groq, Ollama, etc.)."""

    provider_name: str = "openai"
    is_mock: bool = False

    def __init__(self, api_key: str, model_name: str = "gpt-4o-mini", base_url: str = "https://api.openai.com/v1", temperature: float = 0.2, max_tokens: int = 600):
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.fallback = MockLLMClient()

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: StructuredRecipeContext,
        task: AssistantTask,
        question: Optional[str] = None,
    ) -> str:
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    choices = data.get("choices", [])
                    if choices and "message" in choices[0]:
                        return choices[0]["message"].get("content", "").strip()
                logger.warning(
                    f"OpenAI API returned status {response.status_code}: {response.text}. Falling back to MockLLMClient."
                )
        except Exception as e:
            logger.warning(f"Error calling OpenAI API ({e}). Falling back to MockLLMClient.")

        return self.fallback.generate(system_prompt, user_prompt, context, task, question)


def get_llm_client() -> BaseLLMClient:
    """Factory function instantiating the appropriate LLM client based on configuration."""
    provider = settings.LLM_PROVIDER.lower()
    api_key = settings.LLM_API_KEY.strip()

    if not api_key:
        logger.info("No LLM_API_KEY provided; using deterministic MockLLMClient.")
        return MockLLMClient()

    if provider == "gemini":
        return GeminiClient(
            api_key=api_key,
            model_name=settings.LLM_MODEL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    elif provider == "openai":
        return OpenAIClient(
            api_key=api_key,
            model_name=settings.LLM_MODEL,
            base_url=settings.OPENAI_BASE_URL,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.LLM_MAX_TOKENS,
        )
    elif provider == "groq":
        return GroqRAGClient()
    else:
        logger.info(f"Unrecognized provider '{provider}'; falling back to MockLLMClient.")
        return MockLLMClient()


class GroqRAGClient(BaseLLMClient):
    """
    LLM Client that uses Groq LLM (qwen3.8-27b) with the pre-assembled
    recipe context from AssistantService (Parquet + SQLite + RAG knowledge base).

    The service.py already builds a rich user_prompt containing:
      - Full recipe details (title, ingredients, directions)
      - Pantry match info (matched/missing ingredients)
      - RAG knowledge base docs
      - Query intent & entities

    So we simply pass that assembled prompt directly to Groq — no need
    for a separate ChromaDB lookup here.
    """

    provider_name: str = "groq"
    model_name: str = "qwen3.8-27b"
    is_mock: bool = False

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        context: "StructuredRecipeContext",
        task: "AssistantTask",
        question: str | None = None,
    ) -> str:
        try:
            import sys
            from pathlib import Path
            root = Path(__file__).resolve().parent.parent.parent.parent.parent
            if str(root) not in sys.path:
                sys.path.insert(0, str(root))

            from src.llm_client import call_llm

            # Use the pre-assembled prompt from service.py directly —
            # it already contains the full recipe context + RAG docs.
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_prompt},
            ]

            return call_llm(messages)

        except Exception as e:
            logger.error(f"GroqRAGClient error: {e}")
            # Graceful fallback to deterministic mock
            return MockLLMClient().generate(system_prompt, user_prompt, context, task, question)

