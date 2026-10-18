import React, { useState, useEffect, useRef } from 'react';
import { Bell, CheckCircle2, AlertTriangle, Sparkles, X } from 'lucide-react';
import { fetchApi } from '../../services/api';

interface AppNotification {
  id: string;
  message: string;
  type: string;
  read: boolean;
  timestamp: string;
}

export const NotificationPanel: React.FC = () => {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);

  const fetchNotifications = async () => {
    try {
      const res = await fetchApi('/api/pantry/notifications');
      if (res.ok) {
        const data = await res.json();
        setNotifications(data);
      }
    } catch (e) {
      console.error('Failed to fetch notifications');
    }
  };

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 10000);
    return () => clearInterval(interval);
  }, []);

  // Handle click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  const handleOpen = async () => {
    const nextState = !isOpen;
    setIsOpen(nextState);
    if (nextState && unreadCount > 0) {
      try {
        await fetchApi('/api/pantry/notifications/read', { method: 'POST' });
        setNotifications(prev => prev.map(n => ({ ...n, read: true })));
      } catch (e) {}
    }
  };

  const unreadCount = notifications.filter(n => !n.read).length;

  return (
    <div ref={panelRef} style={{ position: 'relative', zIndex: 99999 }}>
      <button 
        onClick={handleOpen}
        aria-label="Notifications"
        style={{
          background: 'rgba(255, 255, 255, 0.95)',
          border: '2px solid rgba(245, 158, 11, 0.5)',
          borderRadius: '50%',
          width: '42px',
          height: '42px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#0F172A',
          cursor: 'pointer',
          position: 'relative',
          boxShadow: '0 4px 15px rgba(245, 158, 11, 0.25)',
          transition: 'all 0.2s ease'
        }}
      >
        <Bell size={20} color="#0F172A" />
        {unreadCount > 0 && (
          <span style={{
            position: 'absolute',
            top: '-2px',
            right: '-2px',
            background: '#F97316',
            color: '#FFFFFF',
            fontSize: '11px',
            fontWeight: 'bold',
            width: '18px',
            height: '18px',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 6px rgba(249, 115, 22, 0.5)',
            border: '2px solid #FFFFFF'
          }}>
            {unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div style={{
          position: 'absolute',
          top: '52px',
          right: '0',
          width: '380px',
          maxWidth: 'calc(100vw - 32px)',
          maxHeight: '480px',
          overflowY: 'auto',
          background: '#FFFFFF',
          border: '2px solid rgba(245, 158, 11, 0.7)',
          borderRadius: '16px',
          boxShadow: '0 25px 60px rgba(15, 23, 42, 0.4), 0 0 0 1px rgba(245, 158, 11, 0.25)',
          zIndex: 999999,
          padding: '16px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', paddingBottom: '10px', borderBottom: '1.5px solid rgba(245, 158, 11, 0.25)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Sparkles size={18} color="#D97706" />
              <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 800, color: '#0F172A' }}>
                Pantry Notifications
              </h3>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              {unreadCount > 0 && (
                <span style={{ fontSize: '11px', fontWeight: 700, background: '#FEF3C7', color: '#92400E', padding: '2px 8px', borderRadius: '12px' }}>
                  {unreadCount} new
                </span>
              )}
              <button
                onClick={() => setIsOpen(false)}
                aria-label="Close notifications"
                style={{
                  background: 'transparent',
                  border: 'none',
                  cursor: 'pointer',
                  padding: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: '#64748B',
                  borderRadius: '6px'
                }}
              >
                <X size={18} />
              </button>
            </div>
          </div>

          {notifications.length === 0 ? (
            <div style={{ padding: '28px 16px', textAlign: 'center', color: '#334155', fontSize: '13px', fontWeight: 600 }}>
              🔔 All clear! No expiry alerts right now.
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {notifications.map(n => {
                const cleanMessage = n.message.replace(/['"]+/g, "'");
                const isExpired = n.type === 'expired';

                return (
                  <div key={n.id} style={{
                    padding: '12px 14px',
                    borderRadius: '12px',
                    background: isExpired ? '#FFFBEB' : '#F0FDF4',
                    border: isExpired ? '1.5px solid #FCD34D' : '1.5px solid #86EFAC',
                    boxShadow: '0 2px 8px rgba(0,0,0,0.06)',
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '10px'
                  }}>
                    {isExpired ? (
                      <AlertTriangle size={18} color="#B45309" style={{ marginTop: '2px', flexShrink: 0 }} />
                    ) : (
                      <CheckCircle2 size={18} color="#047857" style={{ marginTop: '2px', flexShrink: 0 }} />
                    )}
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '13px', color: '#0F172A', lineHeight: '1.45', fontWeight: 700 }}>
                        {cleanMessage}
                      </div>
                      <div style={{ fontSize: '11px', color: '#475569', marginTop: '4px', fontWeight: 600 }}>
                        {n.timestamp}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
