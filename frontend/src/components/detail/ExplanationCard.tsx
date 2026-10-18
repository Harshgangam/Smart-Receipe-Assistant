import React from 'react';
import { Award, Sparkles } from 'lucide-react';
import { ExplanationData } from '../../types/recipe';


interface ExplanationCardProps {
  explanation: string;
  explanationData: ExplanationData;
  preferenceExplanation?: string | null;
}

export const ExplanationCard: React.FC<ExplanationCardProps> = ({
  explanation,
  explanationData,
  preferenceExplanation,
}) => {

  return (
    <div className="explanation-box">
      <div className="explanation-title">
        <Award size={18} />
        <span>Why this recipe was recommended (Explainable AI)</span>
      </div>

      {explanationData.why_this_recipe && (
        <div style={{
          background: 'rgba(236, 253, 245, 0.95)',
          border: '1.5px solid #10b981',
          color: '#064e3b',
          padding: '12px 16px',
          borderRadius: '10px',
          fontSize: '0.9rem',
          lineHeight: '1.5',
          fontWeight: '600',
          marginBottom: '14px',
          boxShadow: '0 2px 8px rgba(16, 185, 129, 0.1)'
        }}>
          <Sparkles size={16} style={{ display: 'inline', marginRight: '8px', color: '#059669', verticalAlign: 'text-bottom' }} />
          {explanationData.why_this_recipe}
        </div>
      )}

      <p className="explanation-text" style={{ color: '#0f172a', fontWeight: '500', lineHeight: '1.6' }}>{explanation}</p>
      {preferenceExplanation && !explanation.includes('Personalization:') && (
        <p style={{ marginTop: '0.75rem', fontSize: '0.88rem', color: '#1e40af', fontWeight: '600', background: 'rgba(239, 246, 255, 0.8)', padding: '8px 12px', borderRadius: '8px', border: '1px solid #bfdbfe' }}>
          {preferenceExplanation.startsWith('Personalization:')
            ? preferenceExplanation
            : `Personalization: ${preferenceExplanation}`}
        </p>
      )}


    </div>
  );
};
