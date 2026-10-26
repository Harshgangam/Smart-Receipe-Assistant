import React, { useState, useEffect } from 'react';
import { Sparkles, Leaf, RefreshCw, AlertCircle } from 'lucide-react';
import { SustainabilityMetricsResponse } from '../../types/api';
import { fetchSustainabilityAnalytics } from '../../services/api';

export const SustainabilityDashboard: React.FC = () => {
  const [metrics, setMetrics] = useState<SustainabilityMetricsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchSustainabilityAnalytics();
      setMetrics(data);
    } catch (err: any) {
      console.error('Failed to load sustainability metrics:', err);
      setError('Unable to load sustainability analytics right now. Please ensure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMetrics();
  }, []);

  if (loading) {
    return (
      <div className="cute-sustainability-panel cute-loading-box">
        <Sparkles className="spin-icon text-emerald-500" size={24} />
        <span style={{ color: '#0f172a', fontWeight: 600 }}>Loading verified pantry analytics...</span>
      </div>
    );
  }

  if (error || !metrics) {
    return (
      <div className="cute-sustainability-panel" style={{ textAlign: 'center', padding: '2.5rem' }}>
        <div style={{ display: 'inline-flex', padding: '0.75rem', borderRadius: '50%', background: '#FEE2E2', color: '#DC2626', marginBottom: '1rem' }}>
          <AlertCircle size={28} />
        </div>
        <h3 style={{ color: '#0F172A', fontWeight: 700, marginBottom: '0.5rem' }}>Analytics Unavailable</h3>
        <p style={{ color: '#64748B', maxWidth: '420px', margin: '0 auto 1.5rem auto', fontSize: '0.9rem' }}>
          {error || 'No pantry data found. Prepare your first meal to log pantry activity!'}
        </p>
        <button
          onClick={loadMetrics}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.6rem 1.2rem',
            background: '#10B981',
            color: '#FFFFFF',
            border: 'none',
            borderRadius: '9999px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={16} />
          <span>Retry Loading</span>
        </button>
      </div>
    );
  }

  const trendList = Array.isArray(metrics.sustainability_trend) ? metrics.sustainability_trend : [];
  const totalBarGraphMeals = trendList.reduce((acc, curr) => acc + (Number(curr.rescued_items) || 0), 0);
  const recipesPreparedCount = trendList.length > 0 ? totalBarGraphMeals : Number(metrics.recipes_prepared_count || 0);

  return (
    <div className="cute-sustainability-panel">
      {/* Top Header */}
      <div className="cute-header-row">
        <div>
          <div className="cute-badge-pill">
            <Leaf size={13} className="text-emerald-600" />
            <span>PANTRY INVENTORY & USAGE</span>
          </div>
          <h2 className="cute-dashboard-title">
            🌱 Pantry Utilization & Cooking Analytics
          </h2>
          <p className="cute-dashboard-desc">
            Factual household pantry tracking of ingredients on hand, items cooked, and upcoming expiration dates.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <button
            type="button"
            onClick={loadMetrics}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 14px',
              borderRadius: '12px',
              border: '1.5px solid #CBD5E1',
              background: '#FFFFFF',
              color: '#334155',
              fontSize: '0.85rem',
              fontWeight: 600,
              cursor: 'pointer',
              boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
            }}
            title="Refresh live metrics"
          >
            <RefreshCw size={14} className={loading ? 'spin-icon' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Factual Status Summary Banner */}
      <div className="cute-status-banner">
        <div className="cute-banner-icon-bubble">✨</div>
        <div className="cute-banner-content">
          <strong>Pantry Health Status</strong>
          <p>{metrics.status_summary}</p>
        </div>
      </div>

      {/* Meals Cooked Metric Card */}
      <div className="cute-metrics-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 320px))' }}>
        <div className="cute-metric-card card-lavender">
          <div className="card-top-row">
            <span className="card-emoji">🥗</span>
            <span className="card-mini-badge badge-lavender">Home Cooked</span>
          </div>
          <div className="card-number text-lavender">{recipesPreparedCount}</div>
          <div className="card-label">Meals Cooked</div>
          <div className="card-subtext">Home recipes prepared</div>
        </div>
      </div>


      {/* 7-Day Activity Trend Chart with Real Logged Counts */}
      <div className="cute-chart-section">
        <div className="cute-chart-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '1.1rem' }}>📊</span>
            <h3 className="cute-chart-title">7-Day Pantry Food Rescue & Cooking Activity</h3>
          </div>
          <span className="cute-chart-badge">Daily Meals Cooked</span>
        </div>

        <div className="cute-chart-canvas">
          {trendList.length > 0 ? (
            trendList.map((dayData, idx) => {
              const maxItems = Math.max(1, ...trendList.map(d => d.rescued_items));
              const heightPct = dayData.rescued_items === 0 ? 0 : Math.max(18, Math.min(100, (dayData.rescued_items / maxItems) * 88));

              return (
                <div key={idx} className="cute-chart-col">
                  <div className={`cute-bar-val-chip ${dayData.rescued_items > 0 ? 'has-items' : ''}`}>
                    {dayData.rescued_items}
                  </div>
                  <div className="cute-bar-track">
                    <div
                      className="cute-bar-fill"
                      style={{ height: `${heightPct}%`, display: dayData.rescued_items === 0 ? 'none' : 'block' }}
                      title={`${dayData.day}: ${dayData.rescued_items} meals cooked`}
                    />
                  </div>
                  <span className="cute-day-label">{dayData.day}</span>
                </div>
              );
            })
          ) : (
            <div style={{ textAlign: 'center', color: '#64748b', padding: '24px', width: '100%' }}>
              No recent activity recorded yet. Start cooking recipes to track pantry activity!
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
