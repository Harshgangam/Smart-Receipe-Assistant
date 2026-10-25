import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Sliders, RefreshCw, Sparkles, ShieldCheck, Plus, Check, X, RotateCcw } from 'lucide-react';
import { simulateSandbox, fetchRecipeById } from '../../services/api';
import { RecipeRecommendationItem } from '../../types/recipe';
import { RecipeCard } from '../recommendations/RecipeCard';

const COMMON_ALLERGEN_PRESETS = [
  'Gluten',
  'Dairy',
  'Peanuts',
  'Tree Nuts',
  'Eggs',
  'Soy',
  'Shellfish',
  'Fish',
  'Sesame',
  'Mustard',
  'Potatoes',
  'Mushrooms',
];

interface SandboxPersistedState {
  disabledItems: string[];
  addedItems: string[];
  pantryUsageWeight: number;
  expiryPriorityWeight: number;
  shoppingCostWeight: number;
  dietary: string;
  allergens: string[];
  clusterTab: 'all' | 'pantry' | 'cost' | 'expiry' | 'quick';
  sandboxData: any | null;
}

const STORAGE_KEY = 'pantry_assistant_sandbox_state';

// In-memory module cache guarantees instant synchronous state preservation across route/component unmounts
let inMemorySandboxState: SandboxPersistedState | null = null;

function loadSandboxState(): SandboxPersistedState {
  if (inMemorySandboxState) {
    return inMemorySandboxState;
  }
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === 'object') {
        inMemorySandboxState = parsed;
        return parsed;
      }
    }
  } catch (e) {
    console.warn('Failed to load sandbox state from sessionStorage:', e);
  }
  return {
    disabledItems: [],
    addedItems: [],
    pantryUsageWeight: 0.4,
    expiryPriorityWeight: 0.3,
    shoppingCostWeight: 0.3,
    dietary: '',
    allergens: [],
    clusterTab: 'all',
    sandboxData: null,
  };
}

function saveSandboxState(state: SandboxPersistedState) {
  inMemorySandboxState = state;
  try {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch (e) {
    console.warn('Failed to save sandbox state to sessionStorage:', e);
  }
}

function clearSandboxState() {
  inMemorySandboxState = null;
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch (e) {
    console.warn('Failed to clear sandbox state from sessionStorage:', e);
  }
}

interface LeftoverSandboxProps {
  initialIngredients: string[];
  dietaryPreference?: string | null;
  onSelectRecipe: (recipe: RecipeRecommendationItem, pantryOverride?: string[]) => void;
  onDietaryChange?: (dietary: string) => void;
}

export const LeftoverSandbox: React.FC<LeftoverSandboxProps> = ({
  initialIngredients,
  dietaryPreference,
  onSelectRecipe,
  onDietaryChange,
}) => {
  const activePantry = initialIngredients;
  const initialSaved = useMemo(() => loadSandboxState(), []);

  const [disabledItems, setDisabledItems] = useState<string[]>(initialSaved.disabledItems || []);
  const [newIngredient, setNewIngredient] = useState<string>('');
  const [addedItems, setAddedItems] = useState<string[]>(initialSaved.addedItems || []);

  // Objective Sliders
  const [pantryUsageWeight, setPantryUsageWeight] = useState<number>(initialSaved.pantryUsageWeight ?? 0.4);
  const [expiryPriorityWeight, setExpiryPriorityWeight] = useState<number>(initialSaved.expiryPriorityWeight ?? 0.3);
  const [shoppingCostWeight, setShoppingCostWeight] = useState<number>(initialSaved.shoppingCostWeight ?? 0.3);

  // Filters & Dietary Lock
  const [dietary, setDietary] = useState<string>(initialSaved.dietary || dietaryPreference || '');
  const [allergens, setAllergens] = useState<string[]>(initialSaved.allergens || []);
  const [customAllergen, setCustomAllergen] = useState<string>('');
  const [resetFeedback, setResetFeedback] = useState<boolean>(false);
  const maxTime = 45;

  // Sync dietary if parent changes preference
  useEffect(() => {
    if (dietaryPreference !== undefined && (dietaryPreference || '') !== dietary) {
      setDietary(dietaryPreference || '');
    }
  }, [dietaryPreference]);

  const [loading, setLoading] = useState<boolean>(false);
  const [clusterTab, setClusterTab] = useState<'all' | 'pantry' | 'cost' | 'expiry' | 'quick'>(initialSaved.clusterTab || 'all');
  const [sandboxData, setSandboxData] = useState<any>(initialSaved.sandboxData || null);

  const effectivePantry = useMemo(() => [
    ...activePantry.filter((item) => !disabledItems.includes(item)),
    ...addedItems,
  ], [activePantry, disabledItems, addedItems]);

  const changesCount = disabledItems.length + addedItems.length + allergens.length + (dietary ? 1 : 0);
  const hasChanges = changesCount > 0 || pantryUsageWeight !== 0.4 || expiryPriorityWeight !== 0.3 || shoppingCostWeight !== 0.3;

  // Synchronize state changes to persistence store so navigating to recipe details never resets selections
  useEffect(() => {
    saveSandboxState({
      disabledItems,
      addedItems,
      pantryUsageWeight,
      expiryPriorityWeight,
      shoppingCostWeight,
      dietary,
      allergens,
      clusterTab,
      sandboxData,
    });
  }, [disabledItems, addedItems, pantryUsageWeight, expiryPriorityWeight, shoppingCostWeight, dietary, allergens, clusterTab, sandboxData]);

  const handleSimulate = async () => {
    setLoading(true);
    try {
      const payload = {
        active_pantry: activePantry,
        added_ingredients: addedItems,
        disabled_ingredients: disabledItems,
        dietary_preference: dietary || null,
        allergens: allergens,
        max_cooking_time_minutes: maxTime,
        weights: {
          pantry_usage: pantryUsageWeight,
          expiry_priority: expiryPriorityWeight,
          shopping_cost: shoppingCostWeight,
        },
      };
      const data = await simulateSandbox(payload);
      setSandboxData(data);
    } catch (e) {
      console.error('Sandbox simulation error:', e);
    } finally {
      setLoading(false);
    }
  };

  const isFirstMount = useRef(true);

  // Trigger simulate on filter/item adjustments, but do NOT overwrite existing saved data on mount
  useEffect(() => {
    if (isFirstMount.current) {
      isFirstMount.current = false;
      // If we already have saved sandboxData from earlier in this session, keep it without resetting
      if (sandboxData) {
        return;
      }
    }
    handleSimulate();
  }, [disabledItems, addedItems, dietary, allergens, maxTime, pantryUsageWeight, expiryPriorityWeight, shoppingCostWeight]);

  // If underlying user pantry changed from outside (e.g. pantry management tab), re-simulate
  const prevPantryStr = useRef(activePantry.join(','));
  useEffect(() => {
    const currentStr = activePantry.join(',');
    if (prevPantryStr.current !== currentStr) {
      prevPantryStr.current = currentStr;
      handleSimulate();
    }
  }, [activePantry]);

  const handleResetSandbox = () => {
    setDisabledItems([]);
    setAddedItems([]);
    setPantryUsageWeight(0.4);
    setExpiryPriorityWeight(0.3);
    setShoppingCostWeight(0.3);
    setAllergens([]);
    setCustomAllergen('');
    setClusterTab('all');
    setDietary(dietaryPreference || '');
    if (onDietaryChange && dietaryPreference) {
      onDietaryChange(dietaryPreference);
    }
    setSandboxData(null);
    clearSandboxState();
    setResetFeedback(true);
    setTimeout(() => setResetFeedback(false), 1400);
  };

  const togglePantryItem = (item: string) => {
    if (disabledItems.includes(item)) {
      setDisabledItems(disabledItems.filter((i) => i !== item));
    } else {
      setDisabledItems([...disabledItems, item]);
    }
  };

  const handleAddCustomItem = () => {
    if (newIngredient.trim() && !addedItems.includes(newIngredient.trim())) {
      setAddedItems([...addedItems, newIngredient.trim()]);
      setNewIngredient('');
    }
  };

  const handleAddCustomAllergen = () => {
    const trimmed = customAllergen.trim().toLowerCase();
    if (trimmed && !allergens.includes(trimmed)) {
      setAllergens([...allergens, trimmed]);
      setCustomAllergen('');
    }
  };

  const removeAllergen = (alg: string) => {
    setAllergens(allergens.filter((a) => a !== alg));
  };

  const toggleAllergen = (alg: string) => {
    const key = alg.trim().toLowerCase();
    if (allergens.includes(key)) {
      setAllergens(allergens.filter((a) => a !== key));
    } else {
      setAllergens([...allergens, key]);
    }
  };

  const handleRecipeSelect = async (clickedRecipe: any) => {
    try {
      // If clickedRecipe already has full directions and ingredients, use directly
      if (clickedRecipe.directions && clickedRecipe.directions.length > 0 && clickedRecipe.ingredients && clickedRecipe.ingredients.length > 0) {
        onSelectRecipe(clickedRecipe, effectivePantry);
        return;
      }
      // Otherwise fetch the authoritative full recipe context using effective sandbox ingredients
      const fullContext = await fetchRecipeById(clickedRecipe.recipe_id, effectivePantry);
      if (fullContext) {
        const mergedMatched = (clickedRecipe.matched_ingredients && clickedRecipe.matched_ingredients.length > 0)
          ? clickedRecipe.matched_ingredients
          : (fullContext.matched_ingredients || []);
        const mergedMissing = (clickedRecipe.missing_ingredients && clickedRecipe.missing_ingredients.length > 0)
          ? clickedRecipe.missing_ingredients
          : (fullContext.missing_ingredients || []);

        onSelectRecipe({
          recipe_id: fullContext.recipe_id,
          title: fullContext.title,
          ingredients: fullContext.ingredients || clickedRecipe.ingredients || [],
          directions: fullContext.directions || clickedRecipe.directions || [],
          link: fullContext.link || '',
          source: fullContext.source || 'RecipeNLG',
          ner: fullContext.ner || clickedRecipe.ner || [],
          matched_ingredients: mergedMatched,
          missing_ingredients: mergedMissing,
          missing_count: mergedMissing.length,
          substitutions: fullContext.substitutions || clickedRecipe.substitutions || [],
          ims: clickedRecipe.ims || fullContext.ims || 0,
          pus: clickedRecipe.pus || (clickedRecipe.pantry_usage_score ? clickedRecipe.pantry_usage_score / 100 : 0),
          recommendation_score: clickedRecipe.match_score || fullContext.recommendation_score || 0,
          image_url: clickedRecipe.image_url || fullContext.image_url,
          safety_status: clickedRecipe.safety_status || 'SAFE',
          estimated_missing_cost: clickedRecipe.missing_cost || 0,
          estimated_time_minutes: fullContext.estimated_time_minutes || clickedRecipe.cooking_time_minutes || 30,
          cuisine: fullContext.cuisine,
          dietary_compatibility: fullContext.dietary_compatibility,
          preference_matches: fullContext.preference_matches || {},
          explanation: clickedRecipe.why_recommended || `Optimized meal using active sandbox ingredients.`,
          explanation_data: {
            matched_ingredients: mergedMatched,
            missing_ingredients: mergedMissing,
            matched_count: mergedMatched.length,
            total_recipe_ingredients: (fullContext.ingredients || []).length,
            relevant_pantry_used_count: mergedMatched.length,
            relevant_pantry_total_count: effectivePantry.length,
            ims: clickedRecipe.ims || fullContext.ims || 0,
            pus: clickedRecipe.pus || 0,
            final_score: clickedRecipe.match_score || 0,
            why_this_recipe: clickedRecipe.why_recommended,
            cuisine_bonus: 0,
            time_adjustment: 0,
          },
        }, effectivePantry);
        return;
      }
    } catch (e) {
      console.warn('Could not fetch full recipe context, falling back to cluster item:', e);
    }
    // Fallback if network issue
    onSelectRecipe({
      ...clickedRecipe,
      ingredients: clickedRecipe.ingredients || clickedRecipe.missing_ingredients || [],
      directions: clickedRecipe.directions || ['Prepare ingredients as desired and cook thoroughly until tender and flavorful.'],
      link: clickedRecipe.link || '',
      source: 'RecipeNLG',
      ner: clickedRecipe.ner || [],
      matched_ingredients: clickedRecipe.matched_ingredients || [],
      missing_count: (clickedRecipe.missing_ingredients || []).length,
      substitutions: clickedRecipe.substitutions || [],
      ims: 0,
      pus: (clickedRecipe.pantry_usage_score || 0) / 100,
      recommendation_score: clickedRecipe.match_score || 0,
      preference_matches: {},
      explanation: clickedRecipe.why_recommended || '',
      explanation_data: {
        matched_ingredients: clickedRecipe.matched_ingredients || [],
        missing_ingredients: clickedRecipe.missing_ingredients || [],
        matched_count: (clickedRecipe.matched_ingredients || []).length,
        total_recipe_ingredients: (clickedRecipe.missing_ingredients || []).length,
        relevant_pantry_used_count: 0,
        relevant_pantry_total_count: effectivePantry.length,
        ims: 0,
        pus: (clickedRecipe.pantry_usage_score || 0) / 100,
        final_score: clickedRecipe.match_score || 0,
        why_this_recipe: clickedRecipe.why_recommended,
        cuisine_bonus: 0,
        time_adjustment: 0,
      },
    }, effectivePantry);
  };


  const displayedRecipes: any[] = sandboxData ? (
    clusterTab === 'pantry' ? sandboxData.clusters.max_pantry_use :
    clusterTab === 'cost' ? sandboxData.clusters.low_shopping_cost :
    clusterTab === 'expiry' ? sandboxData.clusters.near_expiry_rescues :
    clusterTab === 'quick' ? sandboxData.clusters.quick_meals :
    sandboxData.top_recommendations
  ) : [];


  return (
    <div className="sandbox-container glass-panel">
      <div className="sandbox-header">
        <div>
          <h2 className="sandbox-title">
            <Sparkles className="icon-sparkle" size={22} />
            Interactive Leftover Combos Sandbox
          </h2>
          <p className="sandbox-subtitle">
            Simulate ingredient toggles, objective weight trade-offs, and allergen hard locks live in real-time.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            type="button"
            className={`btn-reset-sandbox ${hasChanges ? 'has-modifications' : ''} ${resetFeedback ? 'resetting-pulse' : ''}`}
            onClick={handleResetSandbox}
            title="Reset ingredient toggles, sliders, and dietary locks to default"
          >
            <RotateCcw size={15} className={`reset-icon ${resetFeedback ? 'icon-spin-once' : ''}`} />
            <span>
              {resetFeedback
                ? 'Sandbox Reset! ✨'
                : hasChanges
                ? `Reset Sandbox (${changesCount})`
                : 'Reset Sandbox'}
            </span>
          </button>

          <button className="btn-primary" onClick={handleSimulate} disabled={loading}>
            <RefreshCw size={16} className={loading ? 'spin-icon' : ''} />
            <span>{loading ? 'Recalculating...' : 'Recalculate Live'}</span>
          </button>
        </div>
      </div>

      <div className="sandbox-grid">
        {/* Left Column: Interactive Sandbox Controls */}
        <aside className="sandbox-sidebar glass-card">
          {/* Ingredient Toggles */}
          <div className="control-section">
            <h4 className="control-title">1. Toggle Active Pantry Ingredients</h4>
            <p className="control-desc">Click items on/off to see how recipe rankings adapt instantly:</p>

            <div className="sandbox-tag-cloud">
              {activePantry.map((item) => {
                const isDisabled = disabledItems.includes(item);
                return (
                  <button
                    key={item}
                    className={`sandbox-pill ${isDisabled ? 'pill-disabled' : 'pill-active'}`}
                    onClick={() => togglePantryItem(item)}
                  >
                    {isDisabled ? <X size={12} /> : <Check size={12} />}
                    <span>{item}</span>
                  </button>
                );
              })}
            </div>

            {/* Add Hypothetical Extra Ingredient */}
            <div className="input-group" style={{ marginTop: '12px' }}>
              <input
                type="text"
                className="text-input"
                placeholder="Add leftover item (e.g. potato)..."
                value={newIngredient}
                onChange={(e) => setNewIngredient(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') handleAddCustomItem(); }}
              />
              <button type="button" className="btn-primary" onClick={handleAddCustomItem}>
                <Plus size={16} />
              </button>
            </div>

            {addedItems.length > 0 && (
              <div className="sandbox-tag-cloud" style={{ marginTop: '8px' }}>
                {addedItems.map((item) => (
                  <span key={item} className="sandbox-pill pill-added">
                    <Plus size={12} />
                    <span>{item}</span>
                    <X size={12} style={{ cursor: 'pointer' }} onClick={() => setAddedItems(addedItems.filter(i => i !== item))} />
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Multi-Objective Optimization Sliders */}
          <div className="control-section" style={{ borderTop: '1px solid var(--border-glass)', paddingTop: '16px' }}>
            <h4 className="control-title">
              <Sliders size={16} />
              2. Multi-Objective Weight Sliders
            </h4>

            <div className="slider-group">
              <label className="pref-label">
                <span>Pantry Usage Weight (PUS)</span>
                <strong>{(pantryUsageWeight * 100).toFixed(0)}%</strong>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                className="range-slider"
                value={pantryUsageWeight}
                onChange={(e) => setPantryUsageWeight(parseFloat(e.target.value))}
              />
            </div>

            <div className="slider-group">
              <label className="pref-label">
                <span>Near-Expiry Urgency Weight</span>
                <strong>{(expiryPriorityWeight * 100).toFixed(0)}%</strong>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                className="range-slider"
                value={expiryPriorityWeight}
                onChange={(e) => setExpiryPriorityWeight(parseFloat(e.target.value))}
              />
            </div>

            <div className="slider-group">
              <label className="pref-label">
                <span>Minimizing Missing Purchases Weight</span>
                <strong>{(shoppingCostWeight * 100).toFixed(0)}%</strong>
              </label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                className="range-slider"
                value={shoppingCostWeight}
                onChange={(e) => setShoppingCostWeight(parseFloat(e.target.value))}
              />
            </div>
          </div>

          {/* Dietary Safety Lock */}
          <div className="control-section" style={{ borderTop: '1px solid var(--border-glass)', paddingTop: '16px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
              <h4 className="control-title" style={{ margin: 0 }}>
                3. Dietary Safety Lock
              </h4>
              {dietary === 'vegetarian' && (
                <span className="dietary-lock-badge veg-badge">🥦 Compulsory Vegetarian</span>
              )}
              {dietary === 'vegan' && (
                <span className="dietary-lock-badge vegan-badge">🌱 Compulsory Vegan</span>
              )}
            </div>
            <p className="control-desc">
              Strictly blocks non-compliant meals & ensures matching imagery:
            </p>
            <div className="sandbox-dietary-grid">
              {[
                { id: '', label: '🍽️ All Diets' },
                { id: 'vegetarian', label: '🥦 Vegetarian' },
                { id: 'vegan', label: '🌱 Vegan' },
                { id: 'gluten_free', label: '🌾 Gluten-Free' },
              ].map((opt) => (
                <button
                  key={opt.id}
                  type="button"
                  className={`sandbox-diet-btn ${dietary === opt.id ? 'active' : ''}`}
                  onClick={() => {
                    setDietary(opt.id);
                    if (onDietaryChange) onDietaryChange(opt.id);
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Hard Safety & Allergen Gate Controls */}
          <div className="control-section" style={{ borderTop: '1px solid var(--border-glass)', paddingTop: '16px' }}>
            <h4 className="control-title">
              <ShieldCheck size={16} />
              4. Hard Allergen Safety Lock
            </h4>
            <p className="control-desc">
              Enter any custom allergic product to strictly exclude it semantically (derivatives, forms & synonyms):
            </p>

            {/* Custom Allergen Input */}
            <div className="input-group">
              <input
                type="text"
                className="text-input"
                placeholder="Enter allergen (e.g. shrimp, potato, mustard)..."
                value={customAllergen}
                onChange={(e) => setCustomAllergen(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    handleAddCustomAllergen();
                  }
                }}
              />
              <button
                type="button"
                className="btn-primary"
                onClick={handleAddCustomAllergen}
                title="Lock allergen"
                style={{ background: '#DC2626', borderColor: '#DC2626' }}
              >
                <Plus size={16} />
              </button>
            </div>

            {/* Active Locked Allergen Tags */}
            {allergens.length > 0 && (
              <div className="sandbox-tag-cloud" style={{ marginTop: '10px' }}>
                {allergens.map((alg) => (
                  <span key={alg} className="sandbox-pill pill-allergen">
                    <ShieldCheck size={12} />
                    <span style={{ textTransform: 'capitalize' }}>{alg}</span>
                    <button
                      type="button"
                      style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', color: 'inherit' }}
                      onClick={() => removeAllergen(alg)}
                      title={`Unlock ${alg}`}
                    >
                      <X size={12} style={{ marginLeft: '2px' }} />
                    </button>
                  </span>
                ))}
              </div>
            )}

            {/* Quick Presets */}
            <div style={{ marginTop: '10px' }}>
              <span style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-dim)' }}>
                Quick Presets:
              </span>
              <div className="allergen-preset-grid">
                {COMMON_ALLERGEN_PRESETS.map((preset) => {
                  const key = preset.toLowerCase();
                  const isLocked = allergens.includes(key);
                  return (
                    <button
                      key={preset}
                      type="button"
                      className={`allergen-preset-btn ${isLocked ? 'active' : ''}`}
                      onClick={() => toggleAllergen(key)}
                    >
                      {isLocked ? <Check size={11} /> : <Plus size={11} />}
                      <span>{preset}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="allergen-semantic-hint">
              🛡️ <strong>Semantic Guard:</strong> Any ingredient matching your allergens (including sauces, oils, extracts, and derivatives) will be strictly blocked from recommendations.
            </div>
          </div>
        </aside>

        {/* Right Column: Live Recommendation Clusters & Results */}
        <main className="sandbox-main">
          {/* Cluster Selector Tabs */}
          <div className="cluster-nav-tabs">
            <button
              className={`cluster-tab-btn ${clusterTab === 'all' ? 'active' : ''}`}
              onClick={() => setClusterTab('all')}
            >
              🔥 Top Composite Matches
            </button>
            <button
              className={`cluster-tab-btn ${clusterTab === 'pantry' ? 'active' : ''}`}
              onClick={() => setClusterTab('pantry')}
            >
              🌟 Max Pantry Use
            </button>
            <button
              className={`cluster-tab-btn ${clusterTab === 'cost' ? 'active' : ''}`}
              onClick={() => setClusterTab('cost')}
            >
              💰 Lowest Shopping Burden
            </button>
            <button
              className={`cluster-tab-btn ${clusterTab === 'expiry' ? 'active' : ''}`}
              onClick={() => setClusterTab('expiry')}
            >
              ⏳ Near-Expiry Rescues
            </button>
            <button
              className={`cluster-tab-btn ${clusterTab === 'quick' ? 'active' : ''}`}
              onClick={() => setClusterTab('quick')}
            >
              ⚡ Quick Prep (&lt;30m)
            </button>
          </div>

          {/* Distinct Objective Focus Banner */}
          <div style={{
            marginTop: '14px',
            padding: '12px 18px',
            borderRadius: '12px',
            background: clusterTab === 'pantry' ? 'linear-gradient(135deg, rgba(245, 158, 11, 0.12), rgba(251, 191, 36, 0.08))' :
                        clusterTab === 'cost' ? 'linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(96, 165, 250, 0.08))' :
                        clusterTab === 'expiry' ? 'linear-gradient(135deg, rgba(239, 68, 68, 0.12), rgba(248, 113, 113, 0.08))' :
                        clusterTab === 'quick' ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(52, 211, 153, 0.08))' :
                        'linear-gradient(135deg, rgba(147, 51, 234, 0.1), rgba(192, 132, 252, 0.06))',
            border: `1.5px solid ${
              clusterTab === 'pantry' ? '#F59E0B' :
              clusterTab === 'cost' ? '#2563EB' :
              clusterTab === 'expiry' ? '#EF4444' :
              clusterTab === 'quick' ? '#10B981' :
              '#A855F7'
            }`,
            fontSize: '0.88rem',
            color: '#0F172A',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 2px 8px rgba(0,0,0,0.03)'
          }}>
            <div style={{ lineHeight: '1.45' }}>
              <strong style={{ color: clusterTab === 'pantry' ? '#B45309' : clusterTab === 'cost' ? '#1D4ED8' : '#0F172A' }}>
                {clusterTab === 'pantry' ? '🌟 Max Pantry Use Objective:' :
                 clusterTab === 'cost' ? '💰 Lowest Shopping Burden Objective:' :
                 clusterTab === 'expiry' ? '⏳ Near-Expiry Urgency Mode:' :
                 clusterTab === 'quick' ? '⚡ Quick Prep Express Mode:' :
                 '🔥 Top Composite Matches:'}
              </strong>{' '}
              <span style={{ color: '#334155' }}>
                {clusterTab === 'pantry'
                  ? 'Ranks dishes that consume the highest volume and count of your on-hand pantry ingredients (minimizes pantry waste).'
                  : clusterTab === 'cost'
                  ? 'Minimizes grocery shopping! Strictly prioritizes 100% On-Hand meals (0 missing items) and meals needing only 1 store item.'
                  : clusterTab === 'expiry'
                  ? 'Ranks recipes that use up fresh ingredients closest to their expiration date first.'
                  : clusterTab === 'quick'
                  ? 'Ranks effortless, fast home-cooked meals ready in 30 minutes or less.'
                  : 'Balanced multi-objective recommendation using your personalized weight sliders.'}
              </span>
            </div>
            <span style={{ fontSize: '0.8rem', fontWeight: 700, color: '#475569', marginLeft: '16px', whiteSpace: 'nowrap', padding: '3px 8px', background: 'rgba(255,255,255,0.7)', borderRadius: '6px' }}>
              {displayedRecipes.length} meals
            </span>
          </div>

          {/* Live Cluster Grid */}
          <div className="recipe-cards-grid" style={{ marginTop: '16px' }}>
            {displayedRecipes.map((recipe: any) => (
              <RecipeCard
                key={recipe.recipe_id}
                recipe={recipe}
                onSelect={handleRecipeSelect}
              />
            ))}
          </div>

        </main>
      </div>
    </div>
  );
};
