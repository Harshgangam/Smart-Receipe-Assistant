import React from 'react';
import { Sparkles, Utensils, ShieldCheck } from 'lucide-react';

interface WhimsicalHeroBannerProps {
  onExploreRecipes: () => void;
  pantryCount: number;
}

export const WhimsicalHeroBanner: React.FC<WhimsicalHeroBannerProps> = ({ onExploreRecipes, pantryCount }) => {
  const foodDancers = [
    { name: 'Pepperoni Pizza', emoji: '🍕', role: 'Breakdancer', delay: '0s', posClass: 'pos-1' },
    { name: 'Running Taco', emoji: '🌮', role: 'Speed Hopper', delay: '0.3s', posClass: 'pos-2' },
    { name: 'Smiling Ramen', emoji: '🍜', role: 'Noodle Groover', delay: '0.6s', posClass: 'pos-3' },
    { name: 'Juicy Burger', emoji: '🍔', role: 'Bass King', delay: '0.9s', posClass: 'pos-4' },
    { name: 'Groovy Avocado', emoji: '🥑', role: 'Pop & Locker', delay: '1.2s', posClass: 'pos-5' },
    { name: 'Dancing Sushi', emoji: '🍣', role: 'Roll Master', delay: '1.5s', posClass: 'pos-6' },
    { name: 'Golden Donut', emoji: '🍩', role: 'Spin Queen', delay: '1.8s', posClass: 'pos-7' },
    { name: 'Crunch Cookie', emoji: '🍪', role: 'Tap Stepper', delay: '2.1s', posClass: 'pos-8' },
  ];

  return (
    <div className="whimsical-hero-wrapper glass-panel">
      {/* 3D Food Dance Team Stage */}
      <div className="dance-team-stage">
        {/* Animated 3D Dance Floor Ring & Radial Glow */}
        <div className="dance-floor-spotlight" />
        <div className="dance-floor-ring" />

        {/* Center Wok DJ & Whistling Steam Stage */}
        <div className="wok-dj-center">
          <div className="flying-chef-hat-3d">👨‍🍳</div>
          <div className="whistling-wok-3d">🍳</div>
          <div className="wok-steam-particles">🔥🎶✨</div>
        </div>

        {/* 3D Circular Dance Team Ring Orbiting in Motion */}
        <div className="dance-ring-carousel">
          {foodDancers.map((food) => (
            <div
              key={food.name}
              className={`food-dancer-card ${food.posClass}`}
              style={{ animationDelay: food.delay }}
            >
              <div className="dancer-character">
                <span className="dancer-emoji">{food.emoji}</span>
                <span className="dancer-title">{food.name}</span>
                <span className="dancer-tag">{food.role}</span>
              </div>
              <div className="dancer-ground-shadow" />
            </div>
          ))}
        </div>

        {/* Floating Musical Notes & Motion Droplets */}
        <div className="music-note note-1">🎵</div>
        <div className="music-note note-2">🎶</div>
        <div className="music-note note-3">✨</div>
        <div className="music-note note-4">💃</div>
      </div>

      {/* Translucent Glassmorphic Text Panel (Yellow, Orange, White & Black accents) */}
      <div className="hero-text-glass-panel">
        <div className="hero-tag-badge">
          <Sparkles size={14} color="#F59E0B" />
          <span>3D Dance Team & Pantry Rescue Engine</span>
        </div>

        <h2 className="hero-headline">
          Safest, Least Wasteful & Most Practical Recipe Assistant
        </h2>

        <p className="hero-subtext">
          GroundingGraph substitutions, Allergen Hard-Lock safety, Food Waste PUS scoring, and sub-50ms Interactive Leftover Sandbox.
        </p>

        <div className="hero-cta-group">
          <button
            type="button"
            className="cta-liquid-btn main-cta-glow"
            onClick={onExploreRecipes}
          >
            <span>Start Food Rescue</span>
            <Utensils size={18} />
          </button>

          <div className="hero-pantry-pill">
            <ShieldCheck size={16} className="text-success" />
            <span>{pantryCount} Pantry Items Active</span>
          </div>
        </div>
      </div>
    </div>
  );
};
