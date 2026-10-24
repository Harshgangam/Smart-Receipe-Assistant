import React, { useState, useEffect, useRef } from 'react';
import { Search, LayoutDashboard, ShoppingBag, UtensilsCrossed, LineChart, Sparkles, ShoppingCart } from 'lucide-react';
import { Header } from './components/layout/Header';
import { Footer } from './components/layout/Footer';
import { PantryInput } from './components/pantry/PantryInput';
import { PantryTagList } from './components/pantry/PantryTagList';
import { PantryManagement } from './components/pantry/PantryManagement';
import { PreferenceControls } from './components/preferences/PreferenceControls';
import { RecipeCard } from './components/recommendations/RecipeCard';
import { EmptyState } from './components/recommendations/EmptyState';
import { LoadingSkeleton } from './components/common/LoadingSkeleton';
import { ErrorAlert } from './components/common/ErrorAlert';
import { RecipeDetailPage } from './components/detail/RecipeDetailPage';
import { SustainabilityDashboard } from './components/analytics/SustainabilityDashboard';
import { LeftoverSandbox } from './components/sandbox/LeftoverSandbox';
import { MicroShoppingDashboard } from './components/shopping/MicroShoppingDashboard';

import { usePantry } from './hooks/usePantry';
import { usePreferences } from './hooks/usePreferences';
import { useRecommendations } from './hooks/useRecommendations';
import { RecipeRecommendationItem } from './types/recipe';
import { cookRecipe } from './services/api';

import { FloatingFoodStage, FloatingFoodItem } from './components/common/FloatingFoodStage';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'pantry' | 'recipes' | 'sandbox' | 'shopping' | 'analytics'>('dashboard');

  const { ingredients, setIngredients, addIngredient, removeIngredient, clearPantry, addMultiple, setPantry } = usePantry([]);

  const preferences = usePreferences();
  const { data, loading, error, search } = useRecommendations();
  const [selectedRecipe, setSelectedRecipe] = useState<RecipeRecommendationItem | null>(null);
  const [detailPantryOverride, setDetailPantryOverride] = useState<string[] | null>(null);
  const [pantryRefreshKey, setPantryRefreshKey] = useState(0);
  const [inspirationFood, setInspirationFood] = useState<string | null>(null);

  // Guard against React StrictMode double-invocation: prevents cookRecipe from
  // being called twice (which would increment analytics count by 2 instead of 1).
  const cookedInFlight = useRef(false);

  const handleSelectRecipe = (recipe: RecipeRecommendationItem, overridePantry?: string[]) => {
    cookedInFlight.current = false; // reset lock for each new recipe
    setDetailPantryOverride(overridePantry || null);
    setSelectedRecipe(recipe);
  };

  const handleSelectFloatingFood = (item: FloatingFoodItem) => {
    // 1. Reset the user's pantry to this dish's authentic ingredient bundle
    // Eliminates accumulation of previous ingredients (e.g. avocado persisting across all selections)
    setPantry(item.ingredients);

    // 2. Switch to recipes tab and trigger targeted recommendation search with query steering
    setActiveTab('recipes');
    search(item.ingredients, preferences, 12, false, item.query);

    // 3. Show delightful inspiration feedback
    setInspirationFood(item.name);
    setTimeout(() => setInspirationFood(null), 4500);
  };

  // Synchronize browser history and hash for back button navigation
  useEffect(() => {
    const handleHash = () => {
      if (!window.location.hash.startsWith('#recipe-') && selectedRecipe) {
        setSelectedRecipe(null);
        setDetailPantryOverride(null);
      }
    };
    window.addEventListener('hashchange', handleHash);
    return () => window.removeEventListener('hashchange', handleHash);
  }, [selectedRecipe]);

  const handleSearch = () => {
    setActiveTab('recipes');
    search(ingredients, preferences, 12, false);
  };

  const handleAddStaples = () => {
    addMultiple(['tomato', 'garlic', 'onion', 'pasta', 'olive oil', 'chicken']);
  };

  const hasRecommendations = data && data.recommendations && data.recommendations.length > 0;
  const isZeroResults = data && data.recommendations && data.recommendations.length === 0;

  return (
    <div className="app-container">
      {/* Interactive 3D Floating Food Stage with Multi-Motion Bobbing & Click-to-Cook */}
      <FloatingFoodStage onSelectFood={handleSelectFloatingFood} />

      <Header />

      {inspirationFood && (
        <div className="inspiration-toast-banner">
          <Sparkles size={16} className="text-amber-400" />
          <span>Cooking Inspiration: Loading food rescue recipes for <strong>{inspirationFood}</strong>! ✨</span>
        </div>
      )}

      {selectedRecipe ? (
        <RecipeDetailPage
          recipe={selectedRecipe}
          pantryIngredients={detailPantryOverride || ingredients}
          appliedPreferences={{
            cuisine: preferences.cuisine,
            dietary_preference: preferences.dietary,
            max_cooking_time_minutes: preferences.maxCookingTime,
          }}
          onBack={() => {
            setSelectedRecipe(null);
            setDetailPantryOverride(null);
            window.location.hash = activeTab;
          }}
          onCooked={async (usedNer: string[]) => {
            // Prevent double-fire from React StrictMode or any accidental double-click
            if (cookedInFlight.current) return;
            cookedInFlight.current = true;
            try {
              if (selectedRecipe) {
                await cookRecipe(selectedRecipe.recipe_id, selectedRecipe.title, usedNer);
              }
            } catch (e) {
              console.error('Failed to cook recipe:', e);
            }
            for (const ing of usedNer) {
              removeIngredient(ing);
            }
            setPantryRefreshKey((k) => k + 1);
          }}
        />
      ) : (
        <>
          {/* Navigation Tabs Bar */}
          <div className="nav-tab-bar">
            <button
              onClick={() => setActiveTab('dashboard')}
              className={`nav-tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`}
            >
              <LayoutDashboard size={16} />
              <span>Dashboard</span>
            </button>

            <button
              onClick={() => setActiveTab('pantry')}
              className={`nav-tab-btn ${activeTab === 'pantry' ? 'active' : ''}`}
            >
              <ShoppingBag size={16} />
              <span>Pantry Intelligence ({ingredients.length})</span>
            </button>

            <button
              onClick={() => { setActiveTab('recipes'); if (!data) handleSearch(); }}
              className={`nav-tab-btn ${activeTab === 'recipes' ? 'active' : ''}`}
            >
              <UtensilsCrossed size={16} />
              <span>Recipe Recommendations</span>
            </button>

            <button
              onClick={() => setActiveTab('sandbox')}
              className={`nav-tab-btn ${activeTab === 'sandbox' ? 'active' : ''}`}
            >
              <Sparkles size={16} />
              <span>Leftover Sandbox</span>
            </button>

            <button
              onClick={() => setActiveTab('shopping')}
              className={`nav-tab-btn ${activeTab === 'shopping' ? 'active' : ''}`}
            >
              <ShoppingCart size={16} />
              <span>Micro-Shopping ROI</span>
            </button>

            <button
              onClick={() => setActiveTab('analytics')}
              className={`nav-tab-btn ${activeTab === 'analytics' ? 'active' : ''}`}
            >
              <LineChart size={16} />
              <span>Sustainability Analytics</span>
            </button>
          </div>

          {/* Main Tab Views */}
          {activeTab === 'pantry' && (
            <PantryManagement
              key={pantryRefreshKey}
              onPantryChange={(updatedNames) => {
                setIngredients(updatedNames.map((n) => n.toLowerCase().trim()));
              }}
            />
          )}

          {activeTab === 'sandbox' && (
            <LeftoverSandbox
              initialIngredients={ingredients}
              dietaryPreference={preferences.dietary}
              onSelectRecipe={handleSelectRecipe}
              onDietaryChange={(diet) => preferences.setDietary(diet)}
            />
          )}

          {activeTab === 'shopping' && (
            <MicroShoppingDashboard
              candidateRecipes={data?.recommendations || []}
            />
          )}

          {activeTab === 'analytics' && <SustainabilityDashboard />}

          {(activeTab === 'dashboard' || activeTab === 'recipes') && (
            <main className="main-grid">
              {/* Left Column: Pantry & Personalization Controls */}
              <aside className="sidebar-card glass-panel">
                <div>
                  <div className="section-header">
                    <h2 className="section-title">Your Kitchen Pantry</h2>
                    <span className="section-badge">{ingredients.length} items</span>
                  </div>
                  <PantryInput
                    onAdd={(rawItem, expiryDays) => {
                      const added = addIngredient(rawItem, expiryDays);
                      if (added) {
                        setPantryRefreshKey((k) => k + 1);
                      }
                      return added;
                    }}
                  />
                </div>

                <PantryTagList
                  ingredients={ingredients}
                  onRemove={(item) => {
                    removeIngredient(item);
                    setPantryRefreshKey((k) => k + 1);
                  }}
                  onClear={() => {
                    clearPantry();
                    setPantryRefreshKey((k) => k + 1);
                  }}
                />

                <div style={{ borderTop: '1px solid var(--border-glass)', paddingTop: '1.5rem' }}>
                  <PreferenceControls
                    cuisine={preferences.cuisine}
                    setCuisine={preferences.setCuisine}
                    dietary={preferences.dietary}
                    setDietary={preferences.setDietary}
                    maxCookingTime={preferences.maxCookingTime}
                    setMaxCookingTime={preferences.setMaxCookingTime}
                    allergens={preferences.allergens}
                    onAddAllergen={preferences.addAllergen}
                    onRemoveAllergen={preferences.removeAllergen}
                    onReset={preferences.resetPreferences}
                  />
                </div>

                <button
                  type="button"
                  className="btn-primary btn-action-full"
                  onClick={() => handleSearch()}
                  disabled={loading || ingredients.length === 0}
                >
                  <Search size={18} />
                  <span>{loading ? 'Finding Recipes...' : `Find Food Rescue Meals (${ingredients.length} Items)`}</span>
                </button>
              </aside>

              {/* Right Column: Recommendations & Results */}
              <section>
                {error && <ErrorAlert message={error} onDismiss={() => {}} />}

                {loading && <LoadingSkeleton />}

                {!loading && !data && (
                  <EmptyState type="initial" />
                )}

                {!loading && isZeroResults && (
                  <EmptyState type="no-results" onAddStaples={handleAddStaples} />
                )}

                {!loading && hasRecommendations && (
                  <div>
                    <div className="results-header">
                      <div>
                        <h2 className="results-count">
                          Ranked Food Rescue Recommendations ({data.recommendations.length})
                        </h2>
                        <span style={{ fontSize: '0.82rem', color: 'var(--text-dim)' }}>
                          Evaluated {data.total_candidates_evaluated} candidates from 2.23M corpus
                        </span>
                      </div>
                    </div>

                    <div className="recipe-cards-grid">
                      {data.recommendations.map((recipe) => (
                        <RecipeCard
                          key={recipe.recipe_id}
                          recipe={recipe}
                          onSelect={handleSelectRecipe}
                        />
                      ))}
                    </div>
                  </div>
                )}
              </section>
            </main>
          )}
        </>
      )}

      <Footer />
    </div>
  );
};

export default App;
