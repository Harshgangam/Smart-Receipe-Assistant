import React, { useState, useEffect } from 'react';
import { Sparkles, TrendingUp, ShieldCheck, Leaf, DollarSign, Award } from 'lucide-react';
import { SustainabilityMetricsResponse } from '../../types/api';
import { fetchSustainabilityAnalytics } from '../../services/api';

export const SustainabilityDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<SustainabilityMetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadMetrics() {
      setLoading(true);
      const data = await fetchSustainabilityAnalytics();
      setMetrics(data);
      setLoading(false);
    }
    loadMetrics();
  }, []);

  if (loading) {
    return (
      <div className="cute-sustainability-panel cute-loading-box">
        <Sparkles className="spin-icon text-emerald-500" size={24} />
        <span style={{ color: '#0f172a', fontWeight: 600 }}>Calculating your household eco-savings...</span>
      </div>
    );
  }

  if (!metrics) return null;

  const avoidedKg = metrics.estimated_food_waste_avoided_kg || (metrics.high_risk_rescued_count * 0.45);
  const estimatedCostSaved = (avoidedKg * 7.5).toFixed(2);
  const estimatedCo2Saved = (avoidedKg * 2.2).toFixed(1);

  return (
    <div className="cute-sustainability-panel">
      {/* Cute Top Header */}
      <div className="cute-header-row">
        <div>
          <div className="cute-badge-pill">
            <Leaf size={13} className="text-emerald-600" />
            <span>ECO HERO TRACKER</span>
          </div>
          <h2 className="cute-dashboard-title">
            🌱 Pantry Sustainability & Eco Analytics
          </h2>
          <p className="cute-dashboard-desc">
            Quantifiable impact metrics tracking your household pantry utilization and zero-waste journey.
          </p>
        </div>

        <div className="cute-hero-trophy">
          <Award size={26} className="trophy-icon" />
          <div className="trophy-text">
            <strong>Eco Star</strong>
            <span>Level 3 Saver</span>
          </div>
        </div>
      </div>

      {/* Cheerful Status Summary Banner */}
      <div className="cute-status-banner">
        <div className="cute-banner-icon-bubble">🍃</div>
        <div className="cute-banner-content">
          <strong>Pantry Health Status</strong>
          <p>{metrics.status_summary}</p>
        </div>
      </div>

      {/* 4 Little and Cute Metric Cards */}
      <div className="cute-metrics-grid">
        {/* Card 1: Rescued Items */}
        <div className="cute-metric-card card-peach">
          <div className="card-top-row">
            <span className="card-emoji">🥑</span>
            <span className="card-mini-badge badge-peach">Saved from Waste</span>
          </div>
          <div className="card-number text-peach">{metrics.high_risk_rescued_count}</div>
          <div className="card-label">High-Risk Items Rescued</div>
          <div className="card-subtext">Cooked before spoiling</div>
        </div>

        {/* Card 2: Pantry Utilization */}
        <div className="cute-metric-card card-sky">
          <div className="card-top-row">
            <span className="card-emoji">🎯</span>
            <span className="card-mini-badge badge-sky">Efficiency</span>
          </div>
          <div className="card-number text-sky">{metrics.pantry_utilization_rate}%</div>
          <div className="card-label">Pantry Utilization Rate</div>
          <div className="card-subtext">Active pantry items cooked</div>
        </div>

        {/* Card 3: Food Waste Avoided */}
        <div className="cute-metric-card card-emerald">
          <div className="card-top-row">
            <span className="card-emoji">⚖️</span>
            <span className="card-mini-badge badge-emerald">Landfill Diverted</span>
          </div>
          <div className="card-number text-emerald">{avoidedKg.toFixed(1)} <span style={{ fontSize: '1rem', fontWeight: 600 }}>kg</span></div>
          <div className="card-label">Food Waste Prevented</div>
          <div className="card-subtext">~{estimatedCo2Saved} kg CO₂ emissions saved</div>
        </div>

        {/* Card 4: Recipes Prepared */}
        <div className="cute-metric-card card-lavender">
          <div className="card-top-row">
            <span className="card-emoji">👨‍🍳</span>
            <span className="card-mini-badge badge-lavender">Home Cooked</span>
          </div>
          <div className="card-number text-lavender">{metrics.recipes_prepared_count}</div>
          <div className="card-label">Food Rescue Meals Cooked</div>
          <div className="card-subtext">Nutritious home meals made</div>
        </div>
      </div>

      {/* Eco Impact Savings Footprint Banner */}
      <div className="cute-impact-chip-banner">
        <div className="impact-bubble">
          <DollarSign size={16} className="text-amber-500" />
          <span>Estimated <strong>${estimatedCostSaved}</strong> saved in grocery waste</span>
        </div>
        <div className="impact-bubble">
          <TrendingUp size={16} className="text-emerald-500" />
          <span><strong>{avoidedKg.toFixed(1)} kg</strong> organic food preserved</span>
        </div>
        <div className="impact-bubble">
          <ShieldCheck size={16} className="text-indigo-500" />
          <span><strong>{metrics.current_high_risk_pantry_count || 0}</strong> items currently near expiry</span>
        </div>
      </div>

      {/* 7-Day Activity Trend Chart with High Contrast & Cute Pill Bars */}
      <div className="cute-chart-section">
        <div className="cute-chart-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.1rem' }}>📊</span>
            <h3 className="cute-chart-title">7-Day Pantry Food Rescue Activity</h3>
          </div>
          <span className="cute-chart-badge">Daily Rescued Count</span>
        </div>

        <div className="cute-chart-canvas">
          {metrics.sustainability_trend && metrics.sustainability_trend.length > 0 ? (
            metrics.sustainability_trend.map((dayData, idx) => {
              const maxItems = Math.max(1, ...metrics.sustainability_trend.map(d => d.rescued_items));
              const heightPct = Math.max(18, Math.min(100, (dayData.rescued_items / maxItems) * 88));

              return (
                <div key={idx} className="cute-chart-col">
                  <div className={`cute-bar-val-chip ${dayData.rescued_items > 0 ? 'has-items' : ''}`}>
                    {dayData.rescued_items}
                  </div>
                  <div className="cute-bar-track">
                    <div
                      className="cute-bar-fill"
                      style={{ height: `${heightPct}%` }}
                      title={`${dayData.day}: ${dayData.rescued_items} items rescued`}
                    />
                  </div>
                  <span className="cute-day-label">{dayData.day}</span>
                </div>
              );
            })
          ) : (
            <div style={{ textAlign: 'center', color: '#64748b', padding: '24px', width: '100%' }}>
              No recent activity recorded yet. Start cooking to log your sustainability score!
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
