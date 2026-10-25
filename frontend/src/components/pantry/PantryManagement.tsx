import React, { useState, useEffect, useCallback } from 'react';
import { PantryItem } from '../../types/recipe';
import { fetchPantryItems, addPantryItem, deletePantryItem, clearAllPantryItems, fetchApi } from '../../services/api';

interface PantryManagementProps {
  onPantryChange?: (items: string[]) => void;
}

type FreshnessLevel = 'fresh' | 'few_days_old' | 'use_immediately';

const FRESHNESS_OPTIONS: { key: FreshnessLevel; emoji: string; label: string; color: string; bg: string; multiplier: number }[] = [
  { key: 'fresh',           emoji: '🟢', label: 'Fresh',            color: '#10b981', bg: 'rgba(16,185,129,0.15)',  multiplier: 1.0 },
  { key: 'few_days_old',    emoji: '🟡', label: 'Few Days Old',     color: '#f59e0b', bg: 'rgba(245,158,11,0.15)',  multiplier: 0.5 },
  { key: 'use_immediately', emoji: '🔴', label: 'Use Immediately',  color: '#ef4444', bg: 'rgba(239,68,68,0.15)',   multiplier: 0 },
];

export const PantryManagement: React.FC<PantryManagementProps> = ({ onPantryChange }) => {
  const [items, setItems] = useState<PantryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [category] = useState('Produce');
  const [quantity] = useState(1);
  const [unit] = useState('pcs');
  const [scanMessage] = useState('');

  // Freshness state
  const [freshness, setFreshness] = useState<FreshnessLevel>('fresh');
  const [baseShelfLife, setBaseShelfLife] = useState<number>(7);
  const [fetchingShelfLife, setFetchingShelfLife] = useState(false);

  // Compute final expiry days from freshness selection
  const computedExpiryDays =
    freshness === 'use_immediately' ? 1
    : freshness === 'few_days_old'  ? Math.max(1, Math.floor(baseShelfLife * 0.5))
    : baseShelfLife;

  const loadItems = async () => {
    setLoading(true);
    const data = await fetchPantryItems();
    setItems(data);
    setLoading(false);
    if (onPantryChange) {
      onPantryChange(data.map(i => i.name));
    }
  };

  useEffect(() => { loadItems(); }, []);

  // Auto-fetch shelf life from FoodKeeper whenever ingredient name changes
  const fetchShelfLife = useCallback(async (ingredient: string) => {
    if (!ingredient.trim()) return;
    setFetchingShelfLife(true);
    try {
      const res = await fetchApi(`/api/pantry/shelf-life/${encodeURIComponent(ingredient.trim())}`);
      if (res.ok) {
        const data = await res.json();
        setBaseShelfLife(data.base_shelf_life_days ?? 7);
      }
    } catch (_) {
      setBaseShelfLife(7);
    } finally {
      setFetchingShelfLife(false);
    }
  }, []);

  // Debounce the shelf-life fetch as user types
  useEffect(() => {
    if (!name.trim()) return;
    const timer = setTimeout(() => fetchShelfLife(name), 600);
    return () => clearTimeout(timer);
  }, [name, fetchShelfLife]);

  const handleAdd = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;
    await addPantryItem({ name, category, quantity, unit, expiry_days: computedExpiryDays });
    setName('');
    setFreshness('fresh');
    setBaseShelfLife(7);
    loadItems();
  };

  const handleDelete = async (id: string) => {
    await deletePantryItem(id);
    loadItems();
  };



  const getRiskBadge = (risk: string, days: number) => {
    if (risk === 'high' || days <= 2)
      return <span style={{ background: '#ef4444', color: '#fff', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 600 }}>🔴 High Risk ({days}d)</span>;
    if (risk === 'medium' || days <= 6)
      return <span style={{ background: '#f59e0b', color: '#fff', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 600 }}>🟡 Medium Risk ({days}d)</span>;
    return <span style={{ background: '#10b981', color: '#fff', padding: '2px 8px', borderRadius: '12px', fontSize: '11px', fontWeight: 600 }}>🟢 Fresh ({days}d)</span>;
  };

  return (
    <div style={{ background: 'rgba(255,255,255,0.05)', padding: '24px', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.1)', marginBottom: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '10px' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '20px', fontWeight: 700, color: '#f3f4f6' }}>Dynamic Pantry Intelligence</h2>
          <p style={{ margin: '4px 0 0', color: '#9ca3af', fontSize: '13px' }}>Monitor quantities, categories, and real-time expiry risk levels.</p>
        </div>
        {items.length > 0 && (
          <button
            type="button"
            onClick={async () => {
              if (window.confirm("Are you sure you want to clear all " + items.length + " items from your kitchen pantry?")) {
                await clearAllPantryItems();
                await loadItems();
              }
            }}
            style={{
              background: 'rgba(239, 68, 68, 0.12)',
              border: '1.5px solid #ef4444',
              color: '#f87171',
              padding: '8px 14px',
              borderRadius: '8px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              transition: 'all 0.2s',
            }}
          >
            🗑️ Clear Entire Pantry ({items.length})
          </button>
        )}
      </div>

      {scanMessage && (
        <div style={{ background: 'rgba(99,102,241,0.15)', border: '1px solid #6366f1', color: '#c7d2fe', padding: '12px', borderRadius: '8px', marginBottom: '16px', fontSize: '13px' }}>
          {scanMessage}
        </div>
      )}

      {/* Add Item Form */}
      <form onSubmit={handleAdd}>
        {/* Row 1: Name + Category + Qty + Unit */}
        <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 0.6fr 0.6fr', gap: '8px', marginBottom: '12px' }}>
          <div style={{ position: 'relative' }}>
            <input
              type="text"
              placeholder="Ingredient name (e.g. Spinach)"
              value={name}
              onChange={e => setName(e.target.value)}
              style={{ width: '100%', boxSizing: 'border-box', background: 'rgba(0,0,0,0.3)', border: '1px solid rgba(255,255,255,0.15)', color: '#fff', padding: '9px 12px', borderRadius: '6px' }}
            />
            {fetchingShelfLife && (
              <span style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', fontSize: '11px', color: '#9ca3af' }}>
                looking up...
              </span>
            )}
          </div>
        </div>

        {/* Row 2: Freshness Buttons */}
        <div style={{ marginBottom: '12px' }}>
          <div style={{ fontSize: '12px', color: '#9ca3af', marginBottom: '6px', fontWeight: 500 }}>
            How fresh is this item?
            {name.trim() && (
              <span style={{ marginLeft: '8px', color: '#6366f1' }}>
                Base shelf life: <strong>{baseShelfLife} days</strong>
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            {FRESHNESS_OPTIONS.map(opt => (
              <button
                key={opt.key}
                type="button"
                onClick={() => setFreshness(opt.key)}
                style={{
                  flex: 1,
                  padding: '8px 10px',
                  borderRadius: '8px',
                  border: freshness === opt.key ? `2px solid ${opt.color}` : '2px solid rgba(255,255,255,0.1)',
                  background: freshness === opt.key ? opt.bg : 'rgba(0,0,0,0.2)',
                  color: freshness === opt.key ? opt.color : '#9ca3af',
                  cursor: 'pointer',
                  fontWeight: freshness === opt.key ? 700 : 400,
                  fontSize: '13px',
                  transition: 'all 0.2s',
                }}
              >
                {opt.emoji} {opt.label}
              </button>
            ))}
          </div>

          {/* Expiry preview */}
          {name.trim() && (
            <div style={{ marginTop: '8px', fontSize: '12px', color: '#9ca3af' }}>
              Estimated expiry:{' '}
              <span style={{
                fontWeight: 700,
                color: computedExpiryDays <= 2 ? '#ef4444' : computedExpiryDays <= 6 ? '#f59e0b' : '#10b981'
              }}>
                {computedExpiryDays} day{computedExpiryDays !== 1 ? 's' : ''} from today
              </span>
            </div>
          )}
        </div>

        {/* Row 3: Submit */}
        <button
          type="submit"
          disabled={!name.trim()}
          style={{ width: '100%', background: name.trim() ? '#10b981' : '#374151', color: '#fff', border: 'none', padding: '10px', borderRadius: '6px', cursor: name.trim() ? 'pointer' : 'not-allowed', fontWeight: 600, fontSize: '14px' }}
        >
          + Add to Pantry
        </button>
      </form>

      {/* Pantry Items Grid */}
      <div style={{ marginTop: '20px' }}>
        {loading ? (
          <div style={{ color: '#9ca3af', textAlign: 'center', padding: '20px' }}>Loading pantry inventory...</div>
        ) : items.length === 0 ? (
          <div style={{ color: '#9ca3af', textAlign: 'center', padding: '20px' }}>No items in pantry yet. Add some above!</div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', gap: '12px' }}>
            {items.map(item => (
              <div key={item.id} style={{ background: 'rgba(0,0,0,0.25)', border: '1px solid rgba(255,255,255,0.08)', padding: '12px 16px', borderRadius: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600, color: '#f3f4f6', fontSize: '14px' }}>{item.name}</div>
                  <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '2px' }}>
                    {item.quantity} {item.unit} • {item.category}
                  </div>
                  <div style={{ marginTop: '6px' }}>{getRiskBadge(item.expiry_risk, item.expiry_days)}</div>
                </div>
                <button
                  onClick={() => handleDelete(item.id)}
                  style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '16px', padding: '4px' }}
                  title="Remove item"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
