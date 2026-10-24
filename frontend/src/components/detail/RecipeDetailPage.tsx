import React, { useState, useEffect, useMemo } from 'react';
import {
  ArrowLeft,
  ExternalLink,
  Search,
  CheckCircle2,
  Bookmark,
  Share2,
  Printer,
  Sparkles,
  Utensils,
  Clock,
  Globe,
  Leaf,
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  RotateCcw,
  Check,
  ChefHat,
  Filter,
  Flame,
  Scale
} from 'lucide-react';
import { RecipeRecommendationItem } from '../../types/recipe';
import { formatScore, formatTime, getDietaryLabel } from '../../utils/formatters';
import { getRecipeImageUrl } from '../../utils/recipeImages';
import { ExplanationCard } from './ExplanationCard';
import { SubstitutionPanel } from './SubstitutionPanel';
import { AiAssistantPanel } from './AiAssistantPanel';
import { scaleIngredient } from '../../utils/ingredientScaler';
import { isSameFood, extractCoreFood } from '../../utils/foodNormalizer';

function checkIngredientOnHand(
  rawIng: string,
  pantryList: string[] = [],
  matchedList: string[] = []
): boolean {
  if (!rawIng) return false;
  const rawLower = rawIng.toLowerCase().trim();
  const rawCore = extractCoreFood(rawIng);

  for (const p of pantryList) {
    if (!p) continue;
    const pLower = p.toLowerCase().trim();
    if (isSameFood(rawIng, p)) return true;
    if (rawCore && (isSameFood(rawCore, p) || rawCore === extractCoreFood(p))) return true;
    if (pLower.length >= 3 && (rawLower.includes(pLower) || (rawCore && pLower.includes(rawCore)))) return true;
    if (rawLower.length >= 3 && pLower.includes(rawLower)) return true;
  }
  for (const m of matchedList) {
    if (!m) continue;
    const mLower = m.toLowerCase().trim();
    if (isSameFood(rawIng, m)) return true;
    if (rawCore && (isSameFood(rawCore, m) || rawCore === extractCoreFood(m))) return true;
    if (mLower.length >= 3 && (rawLower.includes(mLower) || (rawCore && mLower.includes(rawCore)))) return true;
    if (rawLower.length >= 3 && mLower.includes(rawLower)) return true;
  }
  return false;
}

interface RecipeDetailPageProps {
  recipe: RecipeRecommendationItem;
  pantryIngredients?: string[];
  appliedPreferences?: {
    cuisine?: string | null;
    dietary_preference?: string | null;
    max_cooking_time_minutes?: number | null;
  };
  onBack: () => void;
  onCooked?: (usedNer: string[]) => void;
}

export const RecipeDetailPage: React.FC<RecipeDetailPageProps> = ({
  recipe,
  pantryIngredients = [],
  appliedPreferences,
  onBack,
  onCooked,
}) => {
  // Search Bar State
  const [searchQuery, setSearchQuery] = useState('');
  const [filterMode, setFilterMode] = useState<'all' | 'matched' | 'missing' | 'steps'>('all');

  // Interactive Features
  const [servingMultiplier, setServingMultiplier] = useState<number>(1);
  const [isSaved, setIsSaved] = useState<boolean>(false);
  const [copiedLink, setCopiedLink] = useState<boolean>(false);
  const [hasCooked, setHasCooked] = useState<boolean>(false);
  const [completedSteps, setCompletedSteps] = useState<Set<number>>(new Set());
  const [interactiveCookMode, setInteractiveCookMode] = useState<boolean>(false);

  // Keyboard escape & shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onBack();
      if (e.key === '/' && document.activeElement?.tagName !== 'INPUT') {
        e.preventDefault();
        document.getElementById('subpage-recipe-search')?.focus();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onBack]);

  // Sync window URL hash
  useEffect(() => {
    window.location.hash = `recipe-${recipe.recipe_id}`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, [recipe.recipe_id]);

  const imageUrl = getRecipeImageUrl(recipe);
  const isNonVeg = recipe.dietary_compatibility === 'non_vegetarian';
  const safetyStatus = recipe.safety_status || 'SAFE';

  // Toggle step completion in Interactive Cooking Mode
  const toggleStep = (idx: number) => {
    setCompletedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  // Compute semantic on-hand and missing counts
  const onHandCount = useMemo(() => {
    const rawList = recipe.ingredients || [];
    return rawList.filter((ing) =>
      checkIngredientOnHand(ing, pantryIngredients, recipe.matched_ingredients)
    ).length;
  }, [recipe.ingredients, pantryIngredients, recipe.matched_ingredients]);

  const missingCount = useMemo(() => {
    const rawList = recipe.ingredients || [];
    return Math.max(0, rawList.length - onHandCount);
  }, [recipe.ingredients, onHandCount]);

  // Filtered ingredients according to search & chips with semantic pantry checking
  const filteredRawIngredients = useMemo(() => {
    const rawList = recipe.ingredients || [];
    const q = searchQuery.toLowerCase().trim();

    return rawList.filter((ing) => {
      const isMatched = checkIngredientOnHand(ing, pantryIngredients, recipe.matched_ingredients);

      if (filterMode === 'matched' && !isMatched) return false;
      if (filterMode === 'missing' && isMatched) return false;

      if (!q) return true;
      return ing.toLowerCase().includes(q);
    });
  }, [recipe.ingredients, pantryIngredients, recipe.matched_ingredients, searchQuery, filterMode]);

  // Filtered and parsed directions according to search
  const filteredDirections = useMemo(() => {
    const rawSteps = recipe.directions || [];
    // Expand any multi-sentence paragraphs into distinct steps if not already split
    const parsedSteps: string[] = [];
    for (const step of rawSteps) {
      if (!step || !step.trim()) continue;
      const cleanStep = step.replace(/^\d+[\.\)]\s*/, '').trim();
      // Split on sentence boundaries (e.g. '. ', '! ', '? ') followed by uppercase or number
      const sentences = cleanStep.split(/(?<=[.!?])\s+(?=[A-Z0-9])/);
      if (sentences.length > 1) {
        for (const s of sentences) {
          const sc = s.trim();
          if (sc) parsedSteps.push(sc);
        }
      } else {
        parsedSteps.push(cleanStep);
      }
    }
    const finalSteps = parsedSteps.length > 0 ? parsedSteps : rawSteps;

    const q = searchQuery.toLowerCase().trim();
    if (!q || filterMode === 'matched' || filterMode === 'missing') return finalSteps;
    return finalSteps.filter((step) => step.toLowerCase().includes(q));
  }, [recipe.directions, searchQuery, filterMode]);

  const handleShare = async () => {
    const shareData = {
      title: `${recipe.title} - AI Pantry Recipe Assistant`,
      text: `Check out this recipe for ${recipe.title} using pantry ingredients!`,
      url: window.location.href,
    };

    if (navigator.share && navigator.canShare && navigator.canShare(shareData)) {
      try {
        await navigator.share(shareData);
        return;
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          console.log('Share error:', err);
        }
      }
    }

    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2500);
    } catch {
      // Fallback if clipboard API is restricted
      const dummy = document.createElement('input');
      document.body.appendChild(dummy);
      dummy.value = window.location.href;
      dummy.select();
      document.execCommand('copy');
      document.body.removeChild(dummy);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2500);
    }
  };

  const handleCookRecipe = () => {
    if (hasCooked) return; // drop duplicate calls (e.g. StrictMode double-invoke)
    setHasCooked(true);
    if (onCooked) onCooked(recipe.ner);
  };

  const totalSteps = recipe.directions?.length || 0;
  const progressPercent = totalSteps > 0 ? Math.round((completedSteps.size / totalSteps) * 100) : 0;

  return (
    <div className="recipe-subpage-container animate-fade-in">
      {/* Sub Web Page Top Navigation Bar */}
      <nav className="subpage-nav-bar glass-neo-panel">
        <div className="subpage-nav-left">
          <button
            onClick={onBack}
            className="neo-btn-back"
            title="Return to recipe recommendations"
          >
            <ArrowLeft size={18} />
            <span>Back to Recommendations</span>
          </button>

          <div className="subpage-breadcrumb">
            <span className="crumb-inactive">Kitchen</span>
            <span className="crumb-sep">/</span>
            <span className="crumb-inactive">Recipes</span>
            <span className="crumb-sep">/</span>
            <span className="crumb-active">{recipe.title}</span>
          </div>
        </div>

        <div className="subpage-nav-actions">
          <button
            onClick={() => setIsSaved(!isSaved)}
            className={`neo-action-btn ${isSaved ? 'neo-btn-saved' : ''}`}
            title="Save to favorites"
          >
            <Bookmark size={16} fill={isSaved ? '#EA580C' : 'none'} />
            <span>{isSaved ? 'Saved in Vault' : 'Save Recipe'}</span>
          </button>

          <button
            onClick={handleShare}
            className="neo-action-btn"
            title="Share Recipe"
          >
            {copiedLink ? <Check size={16} color="#059669" /> : <Share2 size={16} />}
            <span>{copiedLink ? 'Link Copied!' : 'Share'}</span>
          </button>

          <button
            onClick={() => window.print()}
            className="neo-action-btn"
            title="Print recipe card"
          >
            <Printer size={16} />
            <span>Print</span>
          </button>

          {recipe.link ? (
            <a
              href={recipe.link.startsWith('http') ? recipe.link : `https://${recipe.link}`}
              target="_blank"
              rel="noopener noreferrer"
              className="neo-action-btn neo-btn-ghost"
              title="View original recipe source"
            >
              <span>Source</span>
              <ExternalLink size={14} />
            </a>
          ) : (
            <a
              href={`https://www.google.com/search?q=${encodeURIComponent(recipe.title + ' recipe')}`}
              target="_blank"
              rel="noopener noreferrer"
              className="neo-action-btn neo-btn-ghost"
              title="Search recipe on Google"
            >
              <span>Source</span>
              <ExternalLink size={14} />
            </a>
          )}
        </div>
      </nav>

      {/* Hero Showcase Section */}
      <header className="subpage-hero-card glass-neo-panel">
        <div className="subpage-hero-grid">
          {/* Unique Recipe Photo Showcase */}
          <div className="subpage-hero-image-wrapper">
            <img
              src={imageUrl}
              alt={recipe.title}
              className="subpage-hero-image"
              loading="eager"
            />
            <div className="hero-image-gradient-overlay" />

            {/* Food Safety Pill */}
            <div
              className={`subpage-safety-pill ${
                safetyStatus === 'SAFE'
                  ? 'safety-safe'
                  : safetyStatus === 'CAUTION'
                  ? 'safety-caution'
                  : 'safety-blocked'
              }`}
            >
              {safetyStatus === 'SAFE' ? <ShieldCheck size={14} /> : <ShieldAlert size={14} />}
              <span>{safetyStatus} FOOD SAFETY</span>
            </div>

            {/* Floating Match Score Ring */}
            <div className="hero-score-badge">
              <span className="hero-score-num">{formatScore(recipe.recommendation_score)}</span>
              <span className="hero-score-label">MATCH SCORE</span>
            </div>
          </div>

          {/* Hero Recipe Metadata & Overview */}
          <div className="subpage-hero-details">
            <div className="subpage-hero-tags">
              {recipe.cuisine && (
                <span className="neo-tag neo-tag-primary">
                  <Globe size={13} />
                  <span>{recipe.cuisine} Cuisine</span>
                </span>
              )}
              {recipe.estimated_time_minutes ? (
                <span className="neo-tag neo-tag-neutral">
                  <Clock size={13} />
                  <span>{formatTime(recipe.estimated_time_minutes)}</span>
                </span>
              ) : null}
              <span className={`neo-tag ${isNonVeg ? 'neo-tag-neutral' : 'neo-tag-accent'}`}>
                {isNonVeg ? <Utensils size={13} /> : <Leaf size={13} />}
                <span>{getDietaryLabel(recipe.dietary_compatibility)}</span>
              </span>
            </div>

            <h1 className="subpage-recipe-title">{recipe.title}</h1>

            {recipe.why_this_recipe && (
              <div className="subpage-why-box">
                <Sparkles size={16} className="text-accent" />
                <p>
                  <strong>Why this recipe:</strong> {recipe.why_this_recipe}
                </p>
              </div>
            )}

            {/* Metric Strip (Glass + Neomorphism) */}
            <div className="subpage-metrics-grid">
              <div className="neo-metric-box">
                <span className="neo-metric-label">Ingredient Match (IMS)</span>
                <span className="neo-metric-value text-accent">{formatScore(recipe.ims)}%</span>
                <span className="neo-metric-sub">Pantry Ingredients Present</span>
              </div>

              <div className="neo-metric-box">
                <span className="neo-metric-label">Pantry Utilized (PUS)</span>
                <span className="neo-metric-value text-primary">{formatScore(recipe.pus)}%</span>
                <span className="neo-metric-sub">Total Pantry Depleted</span>
              </div>

              <div className="neo-metric-box">
                <span className="neo-metric-label">Missing Ingredients</span>
                <span className={`neo-metric-value ${recipe.missing_count === 0 ? 'text-success' : 'text-warning'}`}>
                  {recipe.missing_count === 0 ? '100% On-Hand' : `${recipe.missing_count} needed`}
                </span>
                <span className="neo-metric-sub">
                  Est. shopping: ${recipe.estimated_missing_cost ? recipe.estimated_missing_cost.toFixed(2) : '0.00'}
                </span>
              </div>
            </div>

            {/* Quick Hero Actions */}
            <div className="subpage-hero-action-bar">
              <button
                onClick={handleCookRecipe}
                disabled={hasCooked}
                className={`neo-cook-btn ${hasCooked ? 'neo-cook-btn-done' : ''}`}
              >
                {hasCooked ? (
                  <>
                    <CheckCircle2 size={20} />
                    <span>Cooked & Deducted from Pantry!</span>
                  </>
                ) : (
                  <>
                    <Flame size={20} />
                    <span>I Made This! (Deduct Ingredients)</span>
                  </>
                )}
              </button>

              <button
                onClick={() => {
                  const nextMode = !interactiveCookMode;
                  setInteractiveCookMode(nextMode);
                  if (nextMode) {
                    setTimeout(() => {
                      document.getElementById('cooking-directions-section')?.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                      });
                    }, 50);
                  }
                }}
                className={`neo-mode-btn ${interactiveCookMode ? 'neo-mode-active' : ''}`}
                title="Guided step-by-step interactive cooking mode"
              >
                <ChefHat size={18} />
                <span>{interactiveCookMode ? 'Exit Cooking Mode' : 'Start Guided Cooking'}</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* UNIQUE GLASSMORPHIC + NEOMORPHIC SEARCH & FILTER BAR */}
      <section className="subpage-search-station glass-neo-panel">
        <div className="search-bar-header">
          <div className="search-bar-title-wrap">
            <h2 className="subpage-search-title">Recipe Inspector & Ingredient Search</h2>
            <p className="subpage-search-subtitle">
              Filter ingredients, look up smart swaps, or jump straight to cooking instructions.
            </p>
          </div>

          {/* Servings Scaler Neomorphic Pill Group */}
          <div className="servings-scaler-wrap">
            <span className="scaler-label">
              <Scale size={14} />
              <span>Servings:</span>
            </span>
            <div className="neo-pill-group">
              {[1, 2, 4, 6].map((scale) => (
                <button
                  key={scale}
                  onClick={() => setServingMultiplier(scale)}
                  className={`neo-pill-scale-btn ${servingMultiplier === scale ? 'active' : ''}`}
                >
                  {scale}x
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Unique Neomorphic Inset Search Bar */}
        <div className="neo-search-input-wrapper">
          <Search size={20} className="neo-search-icon" />
          <input
            id="subpage-recipe-search"
            type="text"
            className="neo-search-input"
            placeholder="Search ingredients, steps, or spices (Press '/' to focus)..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="neo-search-clear-btn"
              title="Clear search query"
            >
              <RotateCcw size={16} />
            </button>
          )}
          <span className="neo-search-shortcut-hint">Press /</span>
        </div>

        {/* Search Mode Filter Chips */}
        <div className="subpage-filter-chips">
          <span className="chips-label">
            <Filter size={13} />
            <span>Filter by:</span>
          </span>

          <button
            onClick={() => setFilterMode('all')}
            className={`neo-chip-btn ${filterMode === 'all' ? 'active' : ''}`}
          >
            All Items ({recipe.ingredients?.length || 0})
          </button>

          <button
            onClick={() => setFilterMode('matched')}
            className={`neo-chip-btn ${filterMode === 'matched' ? 'active' : ''}`}
          >
            ✓ In My Pantry ({onHandCount})
          </button>

          <button
            onClick={() => setFilterMode('missing')}
            className={`neo-chip-btn ${filterMode === 'missing' ? 'active' : ''}`}
          >
            ⚠️ Missing Items ({missingCount})
          </button>

          <button
            onClick={() => setFilterMode('steps')}
            className={`neo-chip-btn ${filterMode === 'steps' ? 'active' : ''}`}
          >
            🍳 Cooking Steps ({recipe.directions?.length || 0})
          </button>
        </div>
      </section>

      {/* Main Sub Web Page Content Columns */}
      <div className="subpage-main-layout">
        {/* Left Column: Ingredients & Substitutions */}
        <div className="subpage-left-col">
          {/* Ingredients Section */}
          <section className="glass-neo-panel subpage-section-card">
            <div className="section-title-bar">
              <h3 className="subpage-card-title">
                Ingredients Required
                {servingMultiplier !== 1 && (
                  <span className="scale-indicator">Scaled for {servingMultiplier}x</span>
                )}
              </h3>
              <span className="section-counter-badge">
                {filteredRawIngredients.length} displayed
              </span>
            </div>

            {filteredRawIngredients.length === 0 ? (
              <div className="empty-search-state">
                <p>No ingredients matched &ldquo;{searchQuery}&rdquo;</p>
                <button onClick={() => setSearchQuery('')} className="neo-btn-sm">
                  Clear Search
                </button>
              </div>
            ) : (
              <ul className="subpage-ingredient-list">
                {filteredRawIngredients.map((rawIng, idx) => {
                  const isMatched = checkIngredientOnHand(rawIng, pantryIngredients, recipe.matched_ingredients);
                  const isMissing = !isMatched;

                  return (
                    <li
                      key={idx}
                      className={`neo-ingredient-item ${
                        isMatched
                          ? 'ingredient-on-hand'
                          : isMissing
                          ? 'ingredient-missing'
                          : ''
                      }`}
                    >
                      <div className="ingredient-status-indicator">
                        {isMatched ? (
                          <Check size={14} className="icon-on-hand" />
                        ) : (
                          <AlertTriangle size={14} className="icon-missing" />
                        )}
                      </div>
                      <span className="ingredient-name-text">
                        {scaleIngredient(rawIng, servingMultiplier)}
                      </span>
                      <span className="ingredient-tag-pill">
                        {isMatched ? 'In Pantry' : 'To Buy'}
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>

          {/* Smart Substitutions Panel */}
          <section className="glass-neo-panel subpage-section-card">
            <SubstitutionPanel
              substitutions={recipe.substitutions}
              missingCount={recipe.missing_count}
            />
          </section>

          {/* Grounded AI Assistant Guidance */}
          <section className="glass-neo-panel subpage-section-card">
            <AiAssistantPanel
              recipe={recipe}
              pantryIngredients={pantryIngredients}
              appliedPreferences={appliedPreferences}
            />
          </section>
        </div>

        {/* Right Column: Cooking Steps & Explanations */}
        <div className="subpage-right-col">
          {/* Explanation Card */}
          <section className="glass-neo-panel subpage-section-card">
            <ExplanationCard
              explanation={recipe.explanation}
              explanationData={recipe.explanation_data}
              preferenceExplanation={recipe.preference_explanation}
            />
          </section>

          {/* Step-by-Step Cooking Directions */}
          <section id="cooking-directions-section" className="glass-neo-panel subpage-section-card">
            <div className="section-title-bar">
              <div>
                <h3 className="subpage-card-title">Cooking Directions</h3>
                {interactiveCookMode && (
                  <p className="cook-mode-status">
                    Step {completedSteps.size} of {totalSteps} complete ({progressPercent}%)
                  </p>
                )}
              </div>

              {interactiveCookMode && (
                <div className="cook-progress-bar-wrap">
                  <div
                    className="cook-progress-bar-fill"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              )}
            </div>

            {filteredDirections.length === 0 ? (
              <div className="empty-search-state">
                <p>No cooking steps matched &ldquo;{searchQuery}&rdquo;</p>
                <button onClick={() => setSearchQuery('')} className="neo-btn-sm">
                  Clear Search
                </button>
              </div>
            ) : (
              <div className="subpage-directions-list">
                {filteredDirections.map((stepText, idx) => {
                  const isDone = completedSteps.has(idx);

                  return (
                    <div
                      key={idx}
                      onClick={() => interactiveCookMode && toggleStep(idx)}
                      className={`subpage-direction-card ${
                        interactiveCookMode ? 'interactive-step-card' : ''
                      } ${isDone ? 'step-completed' : ''}`}
                    >
                      <div className="direction-header-row">
                        <div className={`neo-step-badge ${isDone ? 'step-badge-done' : ''}`}>
                          {isDone ? <Check size={16} /> : idx + 1}
                        </div>
                        {interactiveCookMode && (
                          <span className="step-toggle-label">
                            {isDone ? 'Completed' : 'Tap when finished'}
                          </span>
                        )}
                      </div>

                      <p className="step-instruction-body">{stepText}</p>
                    </div>
                  );
                })}
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
};
