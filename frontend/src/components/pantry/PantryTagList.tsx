import React from 'react';
import { X, RotateCcw } from 'lucide-react';

interface PantryTagListProps {
  ingredients: string[];
  onRemove: (item: string) => void;
  onClear: () => void;
}

export const PantryTagList: React.FC<PantryTagListProps> = ({
  ingredients,
  onRemove,
  onClear,
}) => {
  if (ingredients.length === 0) {
    return (
      <div className="tags-container" style={{ alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ color: 'var(--text-dim)', fontSize: '0.82rem' }}>
          No ingredients added yet. Enter items above or click quick-add staples below.
        </span>
      </div>
    );
  }

  return (
    <div>
      <div className="section-header" style={{ marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          {ingredients.length} item{ingredients.length === 1 ? '' : 's'} in pantry
        </span>
        <button
          type="button"
          onClick={onClear}
          className="btn-reset-pantry"
          style={{ padding: '0.22rem 0.55rem', fontSize: '0.75rem' }}
          title="Reset pantry and remove all items"
          aria-label="Reset Pantry (Clear All)"
        >
          <RotateCcw size={12} />
          <span>Reset Pantry</span>
        </button>
      </div>

      <div className="tags-container">
        {ingredients.map((item) => (
          <span key={item} className="pantry-tag">
            <span>{item}</span>
            <button
              type="button"
              className="tag-remove-btn"
              onClick={() => onRemove(item)}
              aria-label={`Remove ${item}`}
            >
              <X size={14} />
            </button>
          </span>
        ))}
      </div>
    </div>
  );
};
