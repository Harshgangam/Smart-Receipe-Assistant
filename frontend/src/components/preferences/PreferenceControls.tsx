import React, { useState } from 'react';
import { SlidersHorizontal, RotateCcw, ShieldCheck, Plus, X } from 'lucide-react';

interface PreferenceControlsProps {
  cuisine: string | null;
  setCuisine: (c: string | null) => void;
  dietary: string | null;
  setDietary: (d: string | null) => void;
  maxCookingTime: number | null;
  setMaxCookingTime: (t: number | null) => void;
  allergens?: string[];
  onAddAllergen?: (allergen: string) => void;
  onRemoveAllergen?: (allergen: string) => void;
  onReset: () => void;
}

const VISUAL_CUISINES = [
  { name: 'Italian', label: 'Italian', icon: '🇮🇹', color: 'orange', gradient: 'linear-gradient(135deg, #fed7aa 0%, #fb923c 100%)' },
  { name: 'Mexican', label: 'Mexican', icon: '🇲🇽', color: 'blue', gradient: 'linear-gradient(135deg, #bae6fd 0%, #38bdf8 100%)' },
  { name: 'Indian', label: 'Indian', icon: '🇮🇳', color: 'gold', gradient: 'linear-gradient(135deg, #fde68a 0%, #eab308 100%)' },
  { name: 'Asian', label: 'Asian', icon: '🥢', color: 'green', gradient: 'linear-gradient(135deg, #a7f3d0 0%, #34d399 100%)' },
  { name: 'American', label: 'American', icon: '🇺🇸', color: 'red', gradient: 'linear-gradient(135deg, #fecdd3 0%, #fb7185 100%)' },
  { name: 'Dessert', label: 'Dessert', icon: '🍰', color: 'purple', gradient: 'linear-gradient(135deg, #ddd6fe 0%, #a78bfa 100%)' },
  { name: null, label: 'Any', icon: '👨‍🍳', color: 'gray', gradient: 'linear-gradient(135deg, #f1f5f9 0%, #cbd5e1 100%)' },
];

const TIME_CAPSULES = [
  { label: 'Any', value: null, color: 'teal' },
  { label: '15m', value: 15, color: 'purple' },
  { label: '30m', value: 30, color: 'gold' },
  { label: '45m', value: 45, color: 'amber' },
  { label: '60m', value: 60, color: 'indigo' },
];

export const PreferenceControls: React.FC<PreferenceControlsProps> = ({
  cuisine,
  setCuisine,
  dietary,
  setDietary,
  maxCookingTime,
  setMaxCookingTime,
  allergens = [],
  onAddAllergen,
  onRemoveAllergen,
  onReset,
}) => {
  const [allergenInput, setAllergenInput] = useState('');
  const hasActivePrefs = Boolean(cuisine || dietary || maxCookingTime || allergens.length > 0);

  const handleAddAllergen = () => {
    if (allergenInput.trim() && onAddAllergen) {
      onAddAllergen(allergenInput.trim());
      setAllergenInput('');
    }
  };

  return (
    <div className="preference-controls-wrapper">
      <div className="section-header">
        <h3 className="section-title">
          <SlidersHorizontal size={18} className="text-primary" />
          <span>Personalization Engine</span>
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span className="section-badge">Interactive</span>
          {hasActivePrefs && (
            <button
              type="button"
              onClick={onReset}
              className="reset-btn"
              title="Reset all preferences"
            >
              <RotateCcw size={13} />
              <span>Reset</span>
            </button>
          )}
        </div>
      </div>

      {/* 1. Reimagined Preferred Cuisine Selectors (2.5D Tactile Cards with Burst Hover Effect) */}
      <div className="pref-field">
        <label className="pref-label">
          <span>Reimagined Cuisine Selectors</span>
          {cuisine && <span className="pref-active-value">{cuisine}</span>}
        </label>
        
        <div className="cuisine-visual-grid">
          {VISUAL_CUISINES.map((c) => {
            const isSelected = (cuisine === c.name) || (c.name === null && cuisine === null);
            return (
              <div
                key={c.label}
                className={`cuisine-2d-card ${isSelected ? 'selected' : ''}`}
                onClick={() => setCuisine(c.name)}
                style={{ background: c.gradient }}
              >
                {/* 2.5D Burst Hover Food Icon Layer */}
                <div className="cuisine-burst-icon">
                  {c.icon}
                </div>
                <span className="cuisine-card-label">{c.label}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 2. Unique Maximum Active Time Grid (Capsule Tracks with Micro-Scale Feedback & Radial Glow) */}
      <div className="pref-field" style={{ marginTop: '1.25rem' }}>
        <label className="pref-label">
          <span>Unique Maximum Active Time Tracks</span>
          <span className="pref-active-value">
            {maxCookingTime ? `≤ ${maxCookingTime} mins` : 'Any window'}
          </span>
        </label>
        
        <div className="time-capsule-track">
          {TIME_CAPSULES.map((opt) => {
            const isActive = maxCookingTime === opt.value;
            return (
              <button
                key={opt.label}
                type="button"
                className={`time-capsule-pill capsule-${opt.color} ${isActive ? 'active-glow' : ''}`}
                onClick={() => setMaxCookingTime(opt.value)}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* 3. Dietary Lifestyle Selector (Liquid Morph Buttons) */}
      <div className="pref-field" style={{ marginTop: '1.25rem' }}>
        <label className="pref-label">
          <span>Dietary Lifestyle</span>
          {dietary && (
            <span className="pref-active-value" style={{ textTransform: 'capitalize' }}>
              {dietary.replace('_', '-')}
            </span>
          )}
        </label>
        <div className="dietary-liquid-grid">
          <button
            type="button"
            className={`liquid-morph-btn ${dietary === null ? 'active' : ''}`}
            onClick={() => setDietary(null)}
          >
            None
          </button>
          <button
            type="button"
            className={`liquid-morph-btn ${dietary === 'vegetarian' ? 'active' : ''}`}
            onClick={() => setDietary(dietary === 'vegetarian' ? null : 'vegetarian')}
          >
            Vegetarian
          </button>
          <button
            type="button"
            className={`liquid-morph-btn ${dietary === 'vegan' ? 'active' : ''}`}
            onClick={() => setDietary(dietary === 'vegan' ? null : 'vegan')}
          >
            Vegan
          </button>
          <button
            type="button"
            className={`liquid-morph-btn ${dietary === 'non_vegetarian' ? 'active' : ''}`}
            onClick={() => setDietary(dietary === 'non_vegetarian' ? null : 'non_vegetarian')}
          >
            Non-Veg
          </button>
        </div>
      </div>

      {/* 4. Hard Allergen Safety Lock */}
      <div className="pref-field" style={{ marginTop: '1.25rem' }}>
        <label className="pref-label">
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <ShieldCheck size={14} style={{ color: '#DC2626' }} />
            <span>Hard Allergen Safety Lock</span>
          </span>
          {allergens.length > 0 && (
            <span className="pref-active-value" style={{ color: '#DC2626' }}>
              {allergens.length} locked
            </span>
          )}
        </label>
        
        {onAddAllergen && (
          <div className="input-group" style={{ marginBottom: '8px' }}>
            <input
              type="text"
              className="text-input"
              placeholder="Lock custom allergen (e.g. shrimp, peanuts)..."
              value={allergenInput}
              onChange={(e) => setAllergenInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleAddAllergen();
                }
              }}
              style={{ fontSize: '0.82rem' }}
            />
            <button
              type="button"
              className="btn-primary"
              onClick={handleAddAllergen}
              title="Lock allergen"
              style={{ background: '#DC2626', borderColor: '#DC2626', padding: '0 10px' }}
            >
              <Plus size={15} />
            </button>
          </div>
        )}

        {allergens.length > 0 && (
          <div className="sandbox-tag-cloud" style={{ marginTop: '6px' }}>
            {allergens.map((alg) => (
              <span key={alg} className="sandbox-pill pill-allergen">
                <ShieldCheck size={11} />
                <span style={{ textTransform: 'capitalize' }}>{alg}</span>
                {onRemoveAllergen && (
                  <button
                    type="button"
                    style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer', display: 'inline-flex', alignItems: 'center', color: 'inherit' }}
                    onClick={() => onRemoveAllergen(alg)}
                    title={`Unlock ${alg}`}
                  >
                    <X size={11} style={{ marginLeft: '2px' }} />
                  </button>
                )}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
