import React, { useState, useRef } from 'react';
import { Camera, Upload, CheckCircle2, AlertTriangle, HelpCircle, Sparkles, Trash2, Plus, ArrowRight, RefreshCw, RotateCcw } from 'lucide-react';
import { uploadVisionImage, confirmVisionPantryUpdates } from '../../services/api';
import { RecipeRecommendationItem } from '../../types/recipe';

interface DetectedItemState {
  raw_name: string;
  name: string;
  canonical_name: string;
  confidence: number;
  confidence_level: 'HIGH' | 'MEDIUM' | 'LOW';
  is_ambiguous: boolean;
  requires_confirmation: boolean;
  review_message?: string;
  container_type: string;
  estimated_count: number | null;
  quantity_unit: string;
  notes?: string;
  suggested_expiry_days: number;
  selected: boolean;
}

interface VisionIntakeDashboardProps {
  onPantryUpdated?: (confirmedNames?: string[], mode?: 'replace' | 'append') => void;
  onRecipesDiscovered?: (recipes: RecipeRecommendationItem[], confirmedNames?: string[], mode?: 'replace' | 'append') => void;
}

export const VisionIntakeDashboard: React.FC<VisionIntakeDashboardProps> = ({
  onPantryUpdated,
  onRecipesDiscovered,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [savingMode, setSavingMode] = useState<'replace' | 'append' | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [detections, setDetections] = useState<DetectedItemState[]>([]);
  const [updateMode] = useState<'replace' | 'append'>('replace');
  const fileInputRef = useRef<HTMLInputElement>(null);

  const selectedCount = detections.filter((d) => d.selected).length;

  const handleResetVision = () => {
    setSelectedFile(null);
    setPreviewUrl(null);
    setDetections([]);
    setErrorMsg(null);
    setSuccessMsg(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      processSelectedFile(e.target.files[0]);
    }
  };

  const processSelectedFile = (file: File) => {
    setErrorMsg(null);
    setSuccessMsg(null);
    setDetections([]);

    // Validate size (10 MB max)
    if (file.size > 10 * 1024 * 1024) {
      setErrorMsg('Image file size exceeds 10 MB limit. Please select a smaller photo.');
      return;
    }

    // Validate type
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      setErrorMsg('Unsupported format. Please upload a JPEG, PNG, or WebP image.');
      return;
    }

    setSelectedFile(file);
    const objectUrl = URL.createObjectURL(file);
    setPreviewUrl(objectUrl);
  };

  const handleUploadAndAnalyze = async () => {
    if (!selectedFile) return;
    setAnalyzing(true);
    setErrorMsg(null);
    setSuccessMsg(null);

    try {
      const formData = new FormData();
      formData.append('file', selectedFile);

      const res = await uploadVisionImage(formData);
      if (res && res.detected_ingredients) {
        const formatted: DetectedItemState[] = res.detected_ingredients.map((item: any) => ({
          raw_name: item.raw_name,
          name: item.name,
          canonical_name: item.canonical_name,
          confidence: item.confidence,
          confidence_level: item.confidence_level || 'MEDIUM',
          is_ambiguous: !!item.is_ambiguous,
          requires_confirmation: !!item.requires_confirmation,
          review_message: item.review_message,
          container_type: item.container_type || 'none',
          estimated_count: item.estimated_count || (item.quantity_unit === 'pieces' ? 1 : null),
          quantity_unit: item.quantity_unit || 'pieces',
          notes: item.notes,
          suggested_expiry_days: item.suggested_expiry_days || 7,
          selected: true, // Default checked for easy approval
        }));

        setDetections(formatted);
        if (formatted.length === 0) {
          setErrorMsg('No recognizable ingredients identified. Try taking a photo closer to the items or ensuring good lighting.');
        }
      }
    } catch (err: any) {
      console.error('Vision analysis error:', err);
      setErrorMsg(err.message || 'Failed to process image with vision service.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleUpdateItem = (index: number, updates: Partial<DetectedItemState>) => {
    setDetections((prev) => {
      const next = [...prev];
      next[index] = { ...next[index], ...updates };
      return next;
    });
  };

  const handleRemoveItem = (index: number) => {
    setDetections((prev) => prev.filter((_, i) => i !== index));
  };

  const handleAddCustomItem = () => {
    setDetections((prev) => [
      ...prev,
      {
        raw_name: 'new item',
        name: 'Fresh Ingredient',
        canonical_name: 'custom',
        confidence: 1.0,
        confidence_level: 'HIGH',
        is_ambiguous: false,
        requires_confirmation: false,
        container_type: 'none',
        estimated_count: 1,
        quantity_unit: 'pieces',
        suggested_expiry_days: 7,
        selected: true,
      },
    ]);
  };

  const handleConfirmToPantry = async (overrideMode?: 'replace' | 'append') => {
    const selectedItems = detections.filter((d) => d.selected && d.name.trim().length > 0);
    if (selectedItems.length === 0) {
      setErrorMsg('Please select at least one ingredient to confirm.');
      return;
    }

    const modeToUse = overrideMode || updateMode || 'replace';
    setSaving(true);
    setSavingMode(modeToUse);
    setErrorMsg(null);
    try {
      const payload = {
        confirmed_items: selectedItems.map((item) => ({
          name: item.name.trim(),
          canonical_name: item.canonical_name,
          category: 'Produce',
          quantity: item.estimated_count || 1.0,
          unit: item.quantity_unit || 'pieces',
          expiry_days: item.suggested_expiry_days || 7,
          confidence: item.confidence,
        })),
        trigger_recipe_recommendations: true,
        mode: modeToUse,
      };

      const confirmedNames = selectedItems.map((item) => item.name.trim());

      const res = await confirmVisionPantryUpdates(payload);
      setSuccessMsg(res.message || `Successfully updated pantry! ${modeToUse === 'replace' ? 'Replaced existing pantry' : 'Added to pantry'} with ${selectedItems.length} verified item(s).`);

      if (onPantryUpdated) {
        onPantryUpdated(confirmedNames, modeToUse);
      }

      if (onRecipesDiscovered) {
        onRecipesDiscovered(res.recommendations?.recommendations || [], confirmedNames, modeToUse);
      }
    } catch (err: any) {
      console.error('Confirmation error:', err);
      setErrorMsg(err.message || 'Failed to update pantry database.');
    } finally {
      setSaving(false);
      setSavingMode(null);
    }
  };

  return (
    <div className="glass-panel" style={{ padding: '2rem', marginBottom: '2rem', background: 'rgba(255, 255, 255, 0.96)', borderRadius: '16px', boxShadow: '0 8px 30px rgba(0, 0, 0, 0.08)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '12px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Camera size={26} style={{ color: '#2563EB' }} />
            <h2 style={{ margin: 0, fontSize: '1.4rem', fontWeight: 700, color: '#0F172A', letterSpacing: '-0.01em' }}>
              Vision Pantry Intake & Food Recognition
            </h2>
          </div>
          <p style={{ margin: '6px 0 0', color: '#475569', fontSize: '0.9rem', lineHeight: '1.5' }}>
            Identify ingredients from your fridge, countertop, transparent containers, and jars with confidence-aware validation.
          </p>
        </div>
        {(previewUrl || detections.length > 0) && (
          <button
            type="button"
            onClick={handleResetVision}
            className="btn-reset-pantry"
            style={{ padding: '8px 16px', fontSize: '0.85rem' }}
            title="Reset scanner and clear image"
          >
            <RotateCcw size={14} />
            <span>Reset Image & Scanner</span>
          </button>
        )}
      </div>

      {errorMsg && (
        <div style={{ background: '#fef2f2', border: '1px solid #f87171', color: '#991b1b', padding: '12px 16px', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.9rem', fontWeight: 500 }}>
          {errorMsg}
        </div>
      )}

      {successMsg && (
        <div style={{ background: '#ecfdf5', border: '1px solid #34d399', color: '#065f46', padding: '12px 16px', borderRadius: '8px', marginBottom: '1.5rem', fontSize: '0.9rem', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle2 size={18} style={{ color: '#059669' }} />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Upload & Preview Dropzone */}
      <div
        style={{
          border: '2px dashed #94a3b8',
          borderRadius: '12px',
          padding: '2rem',
          textAlign: 'center',
          background: 'rgba(248, 250, 252, 0.85)',
          cursor: 'pointer',
          marginBottom: '1.5rem',
          transition: 'all 0.2s ease',
        }}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          onChange={handleFileChange}
          accept="image/jpeg,image/png,image/webp"
          style={{ display: 'none' }}
        />

        {previewUrl ? (
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem' }}>
            <img
              src={previewUrl}
              alt="Pantry Upload Preview"
              style={{ maxHeight: '250px', maxWidth: '100%', borderRadius: '10px', objectFit: 'contain', border: '1px solid #cbd5e1', boxShadow: '0 4px 12px rgba(0,0,0,0.06)' }}
            />
            <div style={{ color: '#334155', fontSize: '0.88rem' }}>
              Selected: <strong style={{ color: '#0F172A' }}>{selectedFile?.name}</strong> ({(selectedFile?.size || 0) / 1024 > 1000 ? `${((selectedFile?.size || 0) / (1024 * 1024)).toFixed(1)} MB` : `${Math.round((selectedFile?.size || 0) / 1024)} KB`})
            </div>
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <span style={{ color: '#2563EB', fontWeight: 600, fontSize: '0.85rem', cursor: 'pointer' }}>Click image to change</span>
              <button
                type="button"
                onClick={(e) => { e.stopPropagation(); handleResetVision(); }}
                className="btn-reset-pantry"
                style={{ padding: '5px 12px', fontSize: '0.8rem' }}
                title="Clear current image"
              >
                <Trash2 size={13} />
                <span>Reset Image</span>
              </button>
            </div>
          </div>
        ) : (
          <div>
            <Upload size={42} style={{ color: '#64748b', margin: '0 auto 12px' }} />
            <div style={{ color: '#0F172A', fontWeight: 700, fontSize: '1.05rem', marginBottom: '6px' }}>
              Click or drag an image here to scan your pantry
            </div>
            <div style={{ color: '#475569', fontSize: '0.85rem' }}>
              Supports photos of refrigerators, countertops, transparent boxes, and pantry jars (JPEG, PNG, WebP up to 10MB)
            </div>
          </div>
        )}
      </div>

      {previewUrl && detections.length === 0 && (
        <button
          type="button"
          onClick={handleUploadAndAnalyze}
          disabled={analyzing}
          style={{
            width: '100%',
            padding: '14px',
            borderRadius: '10px',
            border: 'none',
            background: analyzing ? '#94a3b8' : '#059669',
            color: '#ffffff',
            fontWeight: 700,
            fontSize: '1rem',
            cursor: analyzing ? 'not-allowed' : 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            marginBottom: '1.5rem',
            boxShadow: '0 4px 14px rgba(5, 150, 105, 0.25)',
          }}
        >
          {analyzing ? (
            <>
              <RefreshCw size={20} className="animate-spin" />
              <span>Analyzing Image with Vision Intelligence...</span>
            </>
          ) : (
            <>
              <Sparkles size={20} />
              <span>Run Food Ingredient Recognition</span>
            </>
          )}
        </button>
      )}

      {/* Detections Review Table */}
      {detections.length > 0 && (
        <div style={{ marginTop: '1.5rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h3 style={{ margin: 0, fontSize: '1.15rem', fontWeight: 700, color: '#0F172A' }}>
              Detected Ingredients ({detections.length})
            </h3>
            <button
              type="button"
              onClick={handleAddCustomItem}
              style={{
                background: '#ffffff',
                border: '1px solid #cbd5e1',
                color: '#2563EB',
                padding: '7px 14px',
                borderRadius: '8px',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
                boxShadow: '0 1px 3px rgba(0,0,0,0.06)',
              }}
            >
              <Plus size={15} />
              <span>Add Missed Item</span>
            </button>
          </div>

          <div style={{ overflowX: 'auto', marginBottom: '1.5rem', borderRadius: '10px', border: '1px solid #e2e8f0', background: '#ffffff', boxShadow: '0 1px 4px rgba(0,0,0,0.04)' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e2e8f0', background: '#f8fafc', color: '#334155', fontWeight: 700 }}>
                  <th style={{ padding: '12px 14px', width: '40px' }}>Include</th>
                  <th style={{ padding: '12px 14px' }}>Ingredient</th>
                  <th style={{ padding: '12px 14px' }}>Confidence Status</th>
                  <th style={{ padding: '12px 14px' }}>Quantity</th>
                  <th style={{ padding: '12px 14px' }}>Container Context & Guidance</th>
                  <th style={{ padding: '12px 14px', width: '50px', textAlign: 'center' }}>Remove</th>
                </tr>
              </thead>
              <tbody>
                {detections.map((item, idx) => {
                  const isHigh = item.confidence_level === 'HIGH';
                  const isMedium = item.confidence_level === 'MEDIUM';

                  return (
                    <tr
                      key={idx}
                      style={{
                        borderBottom: '1px solid #f1f5f9',
                        background: item.selected ? '#ffffff' : '#f8fafc',
                        opacity: item.selected ? 1 : 0.6,
                      }}
                    >
                      <td style={{ padding: '12px 14px' }}>
                        <input
                          type="checkbox"
                          checked={item.selected}
                          onChange={(e) => handleUpdateItem(idx, { selected: e.target.checked })}
                          style={{ cursor: 'pointer', width: '18px', height: '18px', accentColor: '#2563EB' }}
                        />
                      </td>

                      <td style={{ padding: '12px 14px' }}>
                        <input
                          type="text"
                          value={item.name}
                          onChange={(e) => handleUpdateItem(idx, { name: e.target.value })}
                          style={{
                            background: '#ffffff',
                            border: '1.5px solid #cbd5e1',
                            color: '#0F172A',
                            padding: '7px 12px',
                            borderRadius: '6px',
                            fontWeight: 600,
                            width: '100%',
                            boxSizing: 'border-box',
                            fontSize: '0.9rem',
                            boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.04)',
                          }}
                        />
                        {item.canonical_name && item.canonical_name !== item.name.toLowerCase() && (
                          <span style={{ fontSize: '0.75rem', color: '#64748b', display: 'block', marginTop: '3px' }}>
                            Canonical: <strong>{item.canonical_name}</strong>
                          </span>
                        )}
                      </td>

                      <td style={{ padding: '12px 14px' }}>
                        <span
                          style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '5px',
                            padding: '4px 10px',
                            borderRadius: '14px',
                            fontSize: '0.78rem',
                            fontWeight: 700,
                            background: isHigh ? '#dcfce7' : isMedium ? '#fef3c7' : '#f1f5f9',
                            color: isHigh ? '#166534' : isMedium ? '#92400e' : '#475569',
                            border: `1px solid ${isHigh ? '#86efac' : isMedium ? '#fcd34d' : '#cbd5e1'}`,
                          }}
                        >
                          {isHigh ? <CheckCircle2 size={13} /> : isMedium ? <AlertTriangle size={13} /> : <HelpCircle size={13} />}
                          <span>{isHigh ? 'High Confidence' : isMedium ? 'Needs Review' : 'Low Confidence'} ({Math.round(item.confidence * 100)}%)</span>
                        </span>
                      </td>

                      <td style={{ padding: '12px 14px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <input
                            type="number"
                            min="0.1"
                            step="0.5"
                            value={item.estimated_count ?? ''}
                            placeholder="Qty"
                            onChange={(e) => handleUpdateItem(idx, { estimated_count: e.target.value ? parseFloat(e.target.value) : null })}
                            style={{
                              width: '65px',
                              background: '#ffffff',
                              border: '1.5px solid #cbd5e1',
                              color: '#0F172A',
                              fontWeight: 600,
                              padding: '6px 8px',
                              borderRadius: '6px',
                              fontSize: '0.88rem',
                              boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.04)',
                            }}
                          />
                          <input
                            type="text"
                            value={item.quantity_unit}
                            onChange={(e) => handleUpdateItem(idx, { quantity_unit: e.target.value })}
                            style={{
                              width: '68px',
                              background: '#ffffff',
                              border: '1.5px solid #cbd5e1',
                              color: '#334155',
                              fontWeight: 500,
                              padding: '6px 8px',
                              borderRadius: '6px',
                              fontSize: '0.88rem',
                              boxShadow: 'inset 0 1px 2px rgba(0,0,0,0.04)',
                            }}
                          />
                        </div>
                      </td>

                      <td style={{ padding: '12px 14px', fontSize: '0.85rem', lineHeight: '1.4' }}>
                        {item.review_message ? (
                          <div style={{ color: '#b45309', fontWeight: 600 }}>
                            {item.review_message}
                          </div>
                        ) : item.container_type && item.container_type !== 'none' ? (
                          <div style={{ color: '#1e293b', fontWeight: 500 }}>
                            Inside {item.container_type.replace('_', ' ')}
                          </div>
                        ) : (
                          <div style={{ color: '#475569' }}>
                            {item.notes || 'Clearly visible'}
                          </div>
                        )}
                      </td>

                      <td style={{ padding: '12px 14px', textAlign: 'center' }}>
                        <button
                          type="button"
                          onClick={() => handleRemoveItem(idx)}
                          style={{
                            background: '#fee2e2',
                            border: '1px solid #fca5a5',
                            color: '#dc2626',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            padding: '6px',
                            display: 'inline-flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                          }}
                          title="Discard item"
                        >
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Direct Working Action Buttons */}
          <div style={{
            display: 'flex',
            flexWrap: 'wrap',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '14px',
            marginTop: '1.75rem',
            paddingTop: '1.5rem',
            borderTop: '1.5px solid #E2E8F0',
          }}>
            <button
              type="button"
              onClick={handleResetVision}
              className="btn-reset-pantry"
              style={{
                padding: '11px 20px',
                fontSize: '0.9rem',
              }}
              title="Reset image and detections"
            >
              <RotateCcw size={15} />
              <span>Reset Image</span>
            </button>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center' }}>
              <button
                type="button"
                onClick={() => handleConfirmToPantry('append')}
                disabled={saving}
                style={{
                  padding: '11px 22px',
                  borderRadius: '8px',
                  border: '1.5px solid #2563EB',
                  background: '#FFFFFF',
                  color: '#2563EB',
                  cursor: saving ? 'not-allowed' : 'pointer',
                  fontWeight: 700,
                  fontSize: '0.92rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 2px 6px rgba(37,99,235,0.1)',
                  transition: 'all 0.15s ease',
                }}
                title="Add verified items to your existing pantry stock"
              >
                {saving && savingMode === 'append' ? (
                  <>
                    <RefreshCw size={17} className="animate-spin" />
                    <span>Adding to Pantry...</span>
                  </>
                ) : (
                  <>
                    <Plus size={17} />
                    <span>Add to Existing Pantry ({selectedCount})</span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={() => handleConfirmToPantry('replace')}
                disabled={saving}
                style={{
                  padding: '11px 26px',
                  borderRadius: '8px',
                  border: 'none',
                  background: 'linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%)',
                  color: '#FFFFFF',
                  cursor: saving ? 'not-allowed' : 'pointer',
                  fontWeight: 700,
                  fontSize: '0.95rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  boxShadow: '0 4px 14px rgba(37,99,235,0.3)',
                  transition: 'all 0.15s ease',
                }}
                title="Wipes previous pantry and sets pantry to strictly these items"
              >
                {saving && savingMode === 'replace' ? (
                  <>
                    <RefreshCw size={18} className="animate-spin" />
                    <span>Replacing Pantry...</span>
                  </>
                ) : (
                  <>
                    <Sparkles size={18} />
                    <span>Replace Pantry ({selectedCount} items) & Discover Recipes</span>
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
