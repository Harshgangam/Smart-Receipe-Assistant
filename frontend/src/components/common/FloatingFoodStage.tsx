import React, { useState } from 'react';

export interface FloatingFoodItem {
  id: string;
  name: string;
  icon: string;
  ingredients: string[];
  query: string;
  colorHint?: string;
  badge?: string;
}

const LEFT_RAIL_ITEMS: FloatingFoodItem[] = [
  { id: 'avocado', name: 'Fresh Avocado', icon: '🥑', ingredients: ['avocado', 'tomato', 'lime', 'onion', 'cilantro'], query: 'avocado', colorHint: '#10B981', badge: 'Creamy & Fresh' },
  { id: 'pizza', name: 'Artisan Pizza', icon: '🍕', ingredients: ['flour', 'cheese', 'tomato sauce', 'olive oil'], query: 'pizza', colorHint: '#F59E0B', badge: 'Stone-Baked' },
  { id: 'ramen', name: 'Miso Ramen', icon: '🍜', ingredients: ['ramen noodles', 'broth', 'green onion', 'soy sauce', 'garlic'], query: 'ramen', colorHint: '#EAB308', badge: 'Warm Broth' },
  { id: 'taco', name: 'Street Tacos', icon: '🌮', ingredients: ['tortillas', 'beans', 'cheese', 'salsa', 'corn'], query: 'tacos', colorHint: '#EF4444', badge: 'Zesty Spiced' },
  { id: 'fries', name: 'Crispy French Fries', icon: '🍟', ingredients: ['potatoes', 'olive oil', 'salt', 'pepper'], query: 'french fries', colorHint: '#FBBF24', badge: 'Golden Crispy' },
  { id: 'curry', name: 'Aromatic Curry', icon: '🍛', ingredients: ['curry powder', 'rice', 'onion', 'garlic', 'coconut milk'], query: 'curry', colorHint: '#D97706', badge: 'Spiced Fragrant' },
  { id: 'dumplings', name: 'Steamed Dumplings', icon: '🥟', ingredients: ['dumpling wrappers', 'cabbage', 'garlic', 'ginger', 'soy sauce'], query: 'dumplings', colorHint: '#14B8A6', badge: 'Tender Dim Sum' },
];

const RIGHT_RAIL_ITEMS: FloatingFoodItem[] = [
  { id: 'salad', name: 'Garden Salad', icon: '🥗', ingredients: ['lettuce', 'cucumber', 'cherry tomatoes', 'olive oil'], query: 'salad', colorHint: '#22C55E', badge: 'Crunchy Greens' },
  { id: 'pancake', name: 'Fluffy Pancakes', icon: '🥞', ingredients: ['flour', 'milk', 'eggs', 'butter', 'maple syrup'], query: 'pancakes', colorHint: '#F59E0B', badge: 'Maple Berry' },
  { id: 'burger', name: 'Brioche Burger', icon: '🍔', ingredients: ['burger buns', 'lettuce', 'tomato', 'cheese', 'onion'], query: 'burger', colorHint: '#F97316', badge: 'Gourmet Bun' },
  { id: 'soup', name: 'Hearty Soup', icon: '🍲', ingredients: ['vegetable broth', 'potatoes', 'carrots', 'celery', 'onion'], query: 'soup', colorHint: '#EA580C', badge: 'Comfort Bowl' },
  { id: 'croissant', name: 'Butter Croissant', icon: '🥐', ingredients: ['butter', 'flour', 'yeast', 'milk', 'sugar'], query: 'croissant', colorHint: '#FBBF24', badge: 'Flaky Pastry' },
  { id: 'pasta', name: 'Garlic Herb Pasta', icon: '🍝', ingredients: ['pasta', 'garlic', 'olive oil', 'parmesan', 'basil'], query: 'pasta', colorHint: '#EC4899', badge: 'Al Dente' },
  { id: 'strawberry', name: 'Wild Strawberries', icon: '🍓', ingredients: ['strawberries', 'cream', 'sugar', 'mint'], query: 'strawberries', colorHint: '#F43F5E', badge: 'Sweet Berry' },
];

interface FloatingFoodStageProps {
  onSelectFood: (item: FloatingFoodItem) => void;
}

export const FloatingFoodStage: React.FC<FloatingFoodStageProps> = ({ onSelectFood }) => {
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [clickedId, setClickedId] = useState<string | null>(null);

  const handleClick = (item: FloatingFoodItem) => {
    setClickedId(item.id);
    setTimeout(() => setClickedId(null), 650);
    onSelectFood(item);
  };

  return (
    <>
      {/* =====================================================================
          BACKGROUND AMBIENT ORBIT STAGE (STRICTLY BEHIND DASHBOARD PANELS)
          ===================================================================== */}
      <div className="bg-floating-food-canvas" aria-hidden="true">
        {/* Soft Ambient Discs */}
        <div className="bg-3d-elements">
          <div className="orb orb-1" />
          <div className="orb orb-2" />
          <div className="orb orb-3" />
          <div className="orb orb-4" />
        </div>

        {/* Circular Orbit Tracks with Ambient Food Icons Spinning STRICTLY in Background */}
        <div className="bg-orbital-food-stage">
          <div className="orbital-ring ring-outer">
            <div className="orbit-item item-pizza">🍕</div>
            <div className="orbit-item item-fries">🍟</div>
            <div className="orbit-item item-drinks">🥤</div>
            <div className="orbit-circle circle-cyan" />
          </div>

          <div className="orbital-ring ring-middle">
            <div className="orbit-item item-burger">🍔</div>
            <div className="orbit-item item-cake">🍰</div>
            <div className="orbit-item item-coke">🧃</div>
            <div className="orbit-circle circle-purple" />
          </div>

          <div className="orbital-ring ring-inner">
            <div className="orbit-circle circle-amber" />
          </div>
        </div>
      </div>

      {/* =====================================================================
          STRUCTURED LEFT CULINARY SHOWCASE RAIL (CLICKABLE RECIPE DISCOVERY)
          ===================================================================== */}
      <aside className="culinary-side-rail rail-left" aria-label="Quick Food Ideas - Savory Staples">
        <div className="rail-header-tag">
          <span className="rail-tag-dot" />
          <span>Quick Cook</span>
        </div>

        <div className="rail-items-col">
          {LEFT_RAIL_ITEMS.map((item, index) => {
            const isHovered = hoveredId === item.id;
            const isClicked = clickedId === item.id;

            return (
              <div key={item.id} className="rail-item-wrapper" style={{ animationDelay: `${index * 0.3}s` }}>
                <button
                  type="button"
                  className={`rail-food-bubble ${isClicked ? 'bubble-clicked' : ''}`}
                  onClick={() => handleClick(item)}
                  onMouseEnter={() => setHoveredId(item.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  title={`Suggest recipes for ${item.name}! ✨`}
                  aria-label={`Suggest recipes for ${item.name}`}
                >
                  <div className="bubble-aura" style={{ background: item.colorHint || '#10B981' }} />
                  <span className="bubble-emoji">{item.icon}</span>

                  {isHovered && (
                    <div className="rail-tooltip tooltip-right">
                      <div className="tooltip-title">✨ Cook {item.name}!</div>
                      <div className="tooltip-sub">{item.badge} • Click to discover</div>
                    </div>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </aside>

      {/* =====================================================================
          STRUCTURED RIGHT CULINARY SHOWCASE RAIL (CLICKABLE RECIPE DISCOVERY)
          ===================================================================== */}
      <aside className="culinary-side-rail rail-right" aria-label="Quick Food Ideas - Comfort & Delights">
        <div className="rail-header-tag">
          <span className="rail-tag-dot dot-amber" />
          <span>Inspiration</span>
        </div>

        <div className="rail-items-col">
          {RIGHT_RAIL_ITEMS.map((item, index) => {
            const isHovered = hoveredId === item.id;
            const isClicked = clickedId === item.id;

            return (
              <div key={item.id} className="rail-item-wrapper" style={{ animationDelay: `${(index + 2) * 0.3}s` }}>
                <button
                  type="button"
                  className={`rail-food-bubble ${isClicked ? 'bubble-clicked' : ''}`}
                  onClick={() => handleClick(item)}
                  onMouseEnter={() => setHoveredId(item.id)}
                  onMouseLeave={() => setHoveredId(null)}
                  title={`Suggest recipes for ${item.name}! ✨`}
                  aria-label={`Suggest recipes for ${item.name}`}
                >
                  <div className="bubble-aura" style={{ background: item.colorHint || '#F59E0B' }} />
                  <span className="bubble-emoji">{item.icon}</span>

                  {isHovered && (
                    <div className="rail-tooltip tooltip-left">
                      <div className="tooltip-title">✨ Cook {item.name}!</div>
                      <div className="tooltip-sub">{item.badge} • Click to discover</div>
                    </div>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      </aside>
    </>
  );
};
