import React from 'react';
import { RefreshCw, Lightbulb } from 'lucide-react';
import { SubstitutionCandidate } from '../../types/recipe';

interface SubstitutionPanelProps {
  substitutions: SubstitutionCandidate[];
  missingCount: number;
}

export const SubstitutionPanel: React.FC<SubstitutionPanelProps> = ({
  substitutions,
  missingCount,
}) => {
  if (missingCount === 0) {
    return null;
  }

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.75rem' }}>
        <RefreshCw size={18} color="var(--color-accent)" />
        <h4 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.05rem', color: '#0F172A', fontWeight: 800 }}>
          Suggested Culinary Substitutions ({substitutions.length})
        </h4>
      </div>

      {substitutions.length === 0 ? (
        <div
          style={{
            padding: '1.25rem',
            background: 'rgba(255, 255, 255, 0.04)',
            borderRadius: 'var(--radius-md)',
            border: '1px dashed var(--border-subtle)',
            fontSize: '0.88rem',
            color: '#0F172A',
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
          }}
        >
          <div style={{ fontWeight: 700, color: '#0F172A' }}>
            No standard culinary substitutions verified for these missing items.
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)' }}>
            To preserve flavor profile and texture without unpredictable culinary outcomes, we recommend adding missing ingredients directly to your shopping list or preparing an alternative recipe from your recommendations.
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {substitutions.map((sub, idx) => (
            <div key={idx} className="substitution-card">
              <div className="sub-header">
                <div className="sub-names">
                  <span style={{ color: 'var(--color-accent)', fontWeight: 700 }}>{sub.missing_ingredient}</span>
                  <span style={{ margin: '0 0.5rem', color: 'var(--text-dim)' }}>&rarr;</span>
                  <span style={{ color: '#0F172A', fontWeight: 800 }}>{sub.substitute}</span>
                </div>
                <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center', flexWrap: 'wrap' }}>
                  {sub.substitution_type && (
                    <span
                      style={{
                        fontSize: '0.7rem',
                        padding: '0.15rem 0.4rem',
                        borderRadius: 'var(--radius-sm)',
                        background: sub.substitution_type === 'direct' ? '#E0F2FE' : sub.substitution_type === 'combination' ? '#F3E8FF' : '#FEF3C7',
                        color: sub.substitution_type === 'direct' ? '#0369A1' : sub.substitution_type === 'combination' ? '#6B21A8' : '#92400E',
                        fontWeight: 700,
                        textTransform: 'capitalize',
                      }}
                    >
                      {sub.substitution_type.replace('_', ' ')}
                    </span>
                  )}
                  {sub.ratio && <span className="sub-ratio-badge">Ratio {sub.ratio}</span>}
                  <span
                    style={{
                      fontSize: '0.72rem',
                      padding: '0.15rem 0.45rem',
                      borderRadius: 'var(--radius-full)',
                      background: sub.confidence === 'high' ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                      color: sub.confidence === 'high' ? '#047857' : '#B45309',
                      textTransform: 'uppercase',
                      fontWeight: 700,
                    }}
                  >
                    {sub.confidence} confidence
                  </span>
                </div>
              </div>
              <p className="sub-reason">{sub.reason}</p>
              {sub.notes && (
                <p style={{ fontSize: '0.78rem', color: '#475569', fontStyle: 'italic', marginTop: '0.2rem' }}>
                  Tip: {sub.notes}
                </p>
              )}
              {sub.shopping_suggestion && (
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.35rem',
                    fontSize: '0.74rem',
                    color: '#64748B',
                    marginTop: '0.35rem',
                    paddingTop: '0.35rem',
                    borderTop: '1px solid #F1F5F9',
                  }}
                >
                  <span style={{ fontWeight: 600 }}>Option:</span> {sub.shopping_suggestion}
                </div>
              )}
            </div>
          ))}

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.4rem',
              fontSize: '0.76rem',
              color: 'var(--text-dim)',
              marginTop: '0.25rem',
            }}
          >
            <Lightbulb size={13} color="var(--color-accent)" />
            <span>
              Substitutions are culinary suggestions and may slightly alter flavor, browning, or texture.
            </span>
          </div>
        </div>
      )}
    </div>
  );
};
