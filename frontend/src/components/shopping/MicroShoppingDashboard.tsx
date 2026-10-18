import React, { useState, useEffect } from 'react';
import { ShoppingBag, TrendingUp, RefreshCw } from 'lucide-react';
import { fetchMicroShoppingPlan } from '../../services/api';
import { RecipeRecommendationItem } from '../../types/recipe';

interface MicroShoppingDashboardProps {
  candidateRecipes: RecipeRecommendationItem[];
}

export const MicroShoppingDashboard: React.FC<MicroShoppingDashboardProps> = ({ candidateRecipes }) => {
  const [loading, setLoading] = useState<boolean>(false);
  const [planData, setPlanData] = useState<any>(null);

  const loadShoppingPlan = async () => {
    if (!candidateRecipes || candidateRecipes.length === 0) return;
    setLoading(true);
    try {
      const candidatesPayload = candidateRecipes.map((r) => ({
        title: r.title,
        missing_ingredients: r.missing_ingredients,
      }));
      const res = await fetchMicroShoppingPlan(candidatesPayload);
      setPlanData(res);
    } catch (e) {
      console.error('Failed to load shopping plan:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadShoppingPlan();
  }, [candidateRecipes]);

  if (!candidateRecipes || candidateRecipes.length === 0) {
    return (
      <div className="glass-panel" style={{ padding: '3rem', textAlign: 'center' }}>
        <ShoppingBag size={48} style={{ color: 'var(--color-primary)', marginBottom: '1rem' }} />
        <h3>No Recipe Candidates Selected for Shopping Plan</h3>
        <p style={{ color: 'var(--text-muted)', marginTop: '0.5rem' }}>
          Find recipe recommendations first, then view your optimized micro-shopping plan and Pantry ROI here.
        </p>
      </div>
    );
  }

  return (
    <div className="shopping-dashboard glass-panel">
      <div className="dashboard-header">
        <div>
          <h2 className="sandbox-title">
            <ShoppingBag className="icon-shopping" size={24} />
            Micro-Shopping & Pantry ROI Optimizer
          </h2>
          <p className="sandbox-subtitle">
            Consolidates missing ingredients across candidate recipes to maximize purchase reuse and minimize package waste.
          </p>
        </div>

        <button className="btn-primary" onClick={loadShoppingPlan} disabled={loading}>
          <RefreshCw size={16} className={loading ? 'spin-icon' : ''} />
          <span>{loading ? 'Optimizing...' : 'Refresh Shopping ROI'}</span>
        </button>
      </div>

      {planData && (
        <div className="shopping-metrics-grid">
          <div className="glass-card metric-card">
            <span className="metric-card-label">Total Unique Items to Buy</span>
            <div className="metric-card-val">{planData.total_unique_items}</div>
            <span className="metric-card-sub">Consolidated across {planData.selected_recipes.length} planned meals</span>
          </div>

          <div className="glass-card metric-card">
            <span className="metric-card-label">Estimated Grocery Cost</span>
            <div className="metric-card-val">${planData.total_estimated_cost.toFixed(2)}</div>
            <span className="metric-card-sub">Optimized package sizes</span>
          </div>

          <div className="glass-card metric-card">
            <span className="metric-card-label">Overall Pantry ROI Score</span>
            <div className="metric-card-val score-highlight">
              <TrendingUp size={20} />
              {planData.pantry_roi_overall}
            </div>
            <span className="metric-card-sub">Multi-meal reuse efficiency ratio</span>
          </div>
        </div>
      )}

      {/* Shopping Plan Table */}
      {planData && (
        <div className="glass-card" style={{ marginTop: '24px', padding: '20px' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '16px', color: '#1F2937' }}>
            🛒 Consolidated Micro-Shopping List & Reuse Highlights
          </h3>

          <div className="shopping-table-wrapper">
            <table className="shopping-table">
              <thead>
                <tr>
                  <th>Missing Ingredient</th>
                  <th>Standard Package</th>
                  <th>Est. Cost</th>
                  <th>Used In Planned Meals</th>
                  <th>Pantry ROI</th>
                  <th>Leftover Risk</th>
                  <th>Optimizer Recommendation</th>
                </tr>
              </thead>
              <tbody>
                {planData.items_to_buy.map((item: any) => (
                  <tr key={item.ingredient}>
                    <td className="font-bold text-main">{item.ingredient}</td>
                    <td>{item.package_size}</td>
                    <td className="font-semibold">${item.estimated_cost.toFixed(2)}</td>
                    <td>
                      <div className="meal-pill-container">
                        {item.used_in_recipes.map((m: string) => (
                          <span key={m} className="meal-tag-pill">{m.length > 25 ? m.slice(0, 25) + '...' : m}</span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <span className={`roi-badge ${item.pantry_roi_score > 20 ? 'roi-high' : 'roi-normal'}`}>
                        {item.pantry_roi_score}
                      </span>
                    </td>
                    <td>
                      <span className={`risk-tag ${item.leftover_risk === 'high' ? 'risk-high' : item.leftover_risk === 'medium' ? 'risk-medium' : 'risk-low'}`}>
                        {item.leftover_risk.toUpperCase()}
                      </span>
                    </td>
                    <td className="text-sm color-muted">{item.recommendation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
