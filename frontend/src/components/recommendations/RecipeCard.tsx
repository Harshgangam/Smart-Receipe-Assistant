import React from 'react';
import { Clock, Globe, Leaf, Utensils, AlertCircle, ShieldCheck, ShieldAlert } from 'lucide-react';
import { RecipeRecommendationItem } from '../../types/recipe';
import { formatScore, formatTime, getDietaryLabel } from '../../utils/formatters';
import { getRecipeImageUrl } from '../../utils/recipeImages';
import { ScoreBadge } from './ScoreBadge';

interface RecipeCardProps {
  recipe: RecipeRecommendationItem;
  onSelect: (recipe: RecipeRecommendationItem) => void;
}

export const RecipeCard: React.FC<RecipeCardProps> = ({ recipe, onSelect }) => {
  const isNonVeg = recipe.dietary_compatibility === 'non_vegetarian';
  const isDietaryCompatible =
    recipe.dietary_compatibility === 'vegan_compatible' ||
    recipe.dietary_compatibility === 'vegetarian_compatible' ||
    isNonVeg;

  const imageUrl = getRecipeImageUrl(recipe);
  const safetyStatus = recipe.safety_status || 'SAFE';
  const missingCost = recipe.estimated_missing_cost || 0;

  return (
    <div
      className="recipe-card glass-card"
      onClick={() => onSelect(recipe)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onSelect(recipe);
      }}
    >
      {/* Recipe Food Image Header */}
      <div className="card-image-wrapper">
        <img
          src={imageUrl}
          alt={recipe.title}
          className="card-recipe-image"
          loading="lazy"
          onError={(e) => {
            (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1498837167922-ddd27525d352?auto=format&fit=crop&w=600&q=80';
          }}
        />
        <div className="card-image-overlay" />

        {/* Safety Badge Floating on Image */}
        <div className={`safety-badge-overlay ${safetyStatus === 'SAFE' ? 'safety-safe' : safetyStatus === 'CAUTION' ? 'safety-caution' : 'safety-blocked'}`}>
          {safetyStatus === 'SAFE' ? <ShieldCheck size={13} /> : <ShieldAlert size={13} />}
          <span>{safetyStatus} SAFETY</span>
        </div>

        {/* Match Score Floating Badge */}
        <div className="card-score-floating" title="Food Rescue Match Score">
          <span className="card-score-num">
            {formatScore(recipe.recommendation_score ?? (recipe as any).match_score)}
          </span>
          <span className="card-score-lbl">MATCH</span>
        </div>
      </div>

      <div className="card-body-content">
        <div className="card-top-bar">
          <div>
            <h3 className="card-title">{recipe.title}</h3>
            <span className="card-source-tag">
              Source: {recipe.source || 'RecipeNLG'}
            </span>
          </div>
        </div>

        {/* Rationale Snippet */}
        {(recipe.why_this_recipe || (recipe as any).why_recommended) && (
          <div className="why-recipe-box">
            💡 <strong>Why:</strong> {
              (recipe.why_this_recipe || (recipe as any).why_recommended).length > 110
                ? (recipe.why_this_recipe || (recipe as any).why_recommended).slice(0, 110) + '...'
                : (recipe.why_this_recipe || (recipe as any).why_recommended)
            }
          </div>
        )}

        {/* Dual Scores Metric Strip */}
        <div className="card-metrics-strip">
          <ScoreBadge
            score={recipe.ims ?? (recipe as any).match_score ?? 0}
            label="Match (IMS)"
            isPercent={true}
          />
          <ScoreBadge
            score={recipe.pus ?? (recipe as any).pantry_usage_score ?? 0}
            label="Pantry (PUS)"
            isPercent={true}
          />
        </div>

        {/* Metadata Pills */}
        <div className="card-tags">
          {recipe.cuisine && (
            <span className="meta-pill pill-warm">
              <Globe size={12} />
              <span>{recipe.cuisine}</span>
            </span>
          )}

          {recipe.estimated_time_minutes ? (
            <span className="meta-pill pill-warm">
              <Clock size={12} />
              <span>{formatTime(recipe.estimated_time_minutes)}</span>
            </span>
          ) : null}

          {isDietaryCompatible && (
            <span className={`meta-pill ${isNonVeg ? 'pill-pink' : 'pill-yellow'}`}>
              {isNonVeg ? <Utensils size={12} /> : <Leaf size={12} />}
              <span>{getDietaryLabel(recipe.dietary_compatibility)}</span>
            </span>
          )}

          {recipe.missing_count > 0 ? (
            <span className="meta-pill pill-orange">
              <AlertCircle size={12} />
              <span>
                {recipe.missing_count} missing (~${missingCost.toFixed(2)})
              </span>
            </span>
          ) : (
            <span className="meta-pill pill-red">
              <ShieldCheck size={12} />
              <span>100% On-Hand</span>
            </span>
          )}
        </div>
      </div>
    </div>
  );
};
