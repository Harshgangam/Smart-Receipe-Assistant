import React, { useEffect, useState } from 'react';
import { ChefHat } from 'lucide-react';
import { checkBackendHealth } from '../../services/api';
import { NotificationPanel } from './NotificationPanel';

export const Header: React.FC = () => {
  const [online, setOnline] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    let failureCount = 0;

    const verifyHealth = () => {
      checkBackendHealth()
        .then(() => {
          failureCount = 0;
          if (isMounted) setOnline(true);
        })
        .catch(() => {
          failureCount += 1;
          // Only show disconnected if 2 consecutive checks fail
          if (isMounted && failureCount >= 2) {
            setOnline(false);
          }
        });
    };

    verifyHealth();
    const intervalId = setInterval(verifyHealth, 4000);

    return () => {
      isMounted = false;
      clearInterval(intervalId);
    };
  }, []);

  return (
    <header className="header-wrapper">
      <div className="brand-section">
        <div className="brand-icon">
          <ChefHat size={28} />
        </div>
        <div>
          <h1 className="brand-title">AI Pantry Recipe Assistant</h1>
          <p className="brand-subtitle">
            Pantry-First Recipe Recommendation & Food Waste Reduction
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        <NotificationPanel />
        <div className="status-badge">
          <span
            className="status-dot"
            style={{ backgroundColor: online ? 'var(--color-primary)' : 'var(--color-error)' }}
          />
          <span>{online ? '2.23M Recipe Corpus Active' : 'Backend Disconnected'}</span>
        </div>
      </div>
    </header>
  );
};
