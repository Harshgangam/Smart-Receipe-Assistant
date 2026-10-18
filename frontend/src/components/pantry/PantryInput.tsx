import React, { useState, useEffect, useCallback } from 'react';
import { Plus } from 'lucide-react';
import { fetchApi } from '../../services/api';

type FreshnessLevel = 'fresh' | 'few_days_old' | 'use_immediately';

interface FreshnessOption {
  key: FreshnessLevel;
  emoji: string;
  label: string;
  color: string;
  bg: string;
}

const FRESHNESS_OPTIONS: FreshnessOption[] = [
  { key: 'fresh',           emoji: '🟢', label: 'Fresh',          color: '#10b981', bg: 'rgba(16,185,129,0.15)' },
  { key: 'few_days_old',    emoji: '🟡', label: 'Few Days Old',   color: '#f59e0b', bg: 'rgba(245,158,11,0.15)' },
  { key: 'use_immediately', emoji: '🔴', label: 'Use Now',        color: '#ef4444', bg: 'rgba(239,68,68,0.15)'  },
];

interface PantryInputProps {
  onAdd: (ingredient: string, expiryDays?: number) => boolean;
}

export const PantryInput: React.FC<PantryInputProps> = ({ onAdd }) => {
  const [value, setValue] = useState('');
  const [freshness, setFreshness] = useState<FreshnessLevel>('fresh');
  const [baseShelfLife, setBaseShelfLife] = useState<number>(7);
  const [fetchingShelfLife, setFetchingShelfLife] = useState(false);
  const [showFreshness, setShowFreshness] = useState(false);

  // Compute final expiry days from freshness button
  const computedExpiryDays =
    freshness === 'use_immediately' ? 1
    : freshness === 'few_days_old'  ? Math.max(1, Math.floor(baseShelfLife * 0.5))
    : baseShelfLife;

  // Auto-fetch shelf life from FoodKeeper as user types (debounced 600ms)
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

  useEffect(() => {
    if (!value.trim()) { setShowFreshness(false); return; }
    setShowFreshness(true);
    const timer = setTimeout(() => fetchShelfLife(value), 600);
    return () => clearTimeout(timer);
  }, [value, fetchShelfLife]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim()) {
      onAdd(value, computedExpiryDays);
      setValue('');
      setFreshness('fresh');
      setBaseShelfLife(7);
      setShowFreshness(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {/* Input row */}
      <div className="input-group">
        <div style={{ position: 'relative', flex: 1 }}>
          <input
            type="text"
            className="text-input"
            placeholder="Add ingredient (e.g. tomato, pasta)..."
            value={value}
            onChange={(e) => setValue(e.target.value)}
            aria-label="Pantry ingredient"
            style={{ width: '100%', boxSizing: 'border-box' }}
          />
          {fetchingShelfLife && (
            <span style={{ position: 'absolute', right: '10px', top: '50%', transform: 'translateY(-50%)', fontSize: '11px', color: '#9ca3af' }}>
              looking up...
            </span>
          )}
        </div>
        <button type="submit" className="btn-primary" disabled={!value.trim()}>
          <Plus size={18} />
          <span>Add</span>
        </button>
      </div>

      {/* Freshness buttons — appear once user starts typing */}
      {showFreshness && (
        <div style={{
          background: 'rgba(255, 255, 255, 0.95)',
          border: '1.5px solid rgba(255, 255, 255, 0.9)',
          borderRadius: '12px',
          padding: '12px 14px',
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.12)',
          marginTop: '4px',
        }}>
          <div style={{
            fontSize: '13px',
            color: '#1e293b',
            fontWeight: 700,
            marginBottom: '8px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span>How fresh is <strong style={{ color: '#0f172a', textDecoration: 'underline' }}>{value}</strong>?</span>
            {!fetchingShelfLife && (
              <span style={{ color: '#2563eb', fontWeight: 800 }}>
                Base shelf life: {baseShelfLife}d
              </span>
            )}
          </div>

          {/* 3 Freshness Buttons */}
          <div style={{ display: 'flex', gap: '8px', marginBottom: '10px' }}>
            {FRESHNESS_OPTIONS.map(opt => {
              const isSelected = freshness === opt.key;
              return (
                <button
                  key={opt.key}
                  type="button"
                  onClick={() => setFreshness(opt.key)}
                  style={{
                    flex: 1,
                    padding: '8px 10px',
                    borderRadius: '10px',
                    border: isSelected ? `2.5px solid ${opt.color}` : '1.5px solid #cbd5e1',
                    background: isSelected ? opt.bg : '#ffffff',
                    color: isSelected ? opt.color : '#1e293b',
                    cursor: 'pointer',
                    fontWeight: isSelected ? 800 : 700,
                    fontSize: '12px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '5px',
                    boxShadow: isSelected ? '0 4px 12px rgba(0,0,0,0.1)' : '0 2px 6px rgba(0,0,0,0.04)',
                    transition: 'all 0.2s ease',
                  }}
                >
                  <span>{opt.emoji}</span>
                  <span style={{ color: isSelected ? opt.color : '#0f172a' }}>{opt.label}</span>
                </button>
              );
            })}
          </div>

          {/* Live expiry preview */}
          <div style={{ fontSize: '12px', color: '#334155', fontWeight: 600 }}>
            Will expire in:{' '}
            <span style={{
              fontWeight: 800,
              fontSize: '13px',
              color: computedExpiryDays <= 2 ? '#dc2626'
                   : computedExpiryDays <= 6 ? '#d97706'
                   : '#059669',
            }}>
              {computedExpiryDays} day{computedExpiryDays !== 1 ? 's' : ''} from today
            </span>
            {' '}— will show live countdown in Pantry Intelligence
          </div>
        </div>
      )}
    </form>
  );
};
