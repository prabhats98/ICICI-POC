/**
 * NodeConfigModal - Premium glassmorphism modal for viewing/editing node configuration.
 * Opens when a workflow node is clicked. Fetches & saves config via the API.
 */

import { useState, useEffect, useCallback } from 'react';
import { getNodeConfig, updateNodeConfig } from '../services/api';

export default function NodeConfigModal({ nodeId, nodeName, onClose }) {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [editedValues, setEditedValues] = useState({});

  // Fetch config on mount
  useEffect(() => {
    if (!nodeId) return;

    const fetchConfig = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getNodeConfig(nodeId);
        setConfig(res.data);
        // Initialize edited values from current config
        const initial = {};
        if (res.data.params) {
          Object.entries(res.data.params).forEach(([key, param]) => {
            initial[key] = param.value;
          });
        }
        setEditedValues(initial);
      } catch (err) {
        setError('Failed to load node configuration');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchConfig();
  }, [nodeId]);

  const handleChange = useCallback((key, value) => {
    setEditedValues((prev) => ({ ...prev, [key]: value }));
    setSaveSuccess(false);
  }, []);

  const handleSave = async () => {
    setSaving(true);
    setSaveSuccess(false);
    try {
      await updateNodeConfig(nodeId, editedValues);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 2000);
    } catch (err) {
      setError('Failed to save configuration');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const renderField = (key, param) => {
    const value = editedValues[key] ?? param.value;

    switch (param.type) {
      case 'toggle':
        return (
          <div className="ncm-field" key={key}>
            <label className="ncm-label">{param.label}</label>
            <button
              type="button"
              className={`ncm-toggle ${value ? 'active' : ''}`}
              onClick={() => handleChange(key, !value)}
            >
              <span className="ncm-toggle-thumb" />
            </button>
          </div>
        );

      case 'slider':
        return (
          <div className="ncm-field" key={key}>
            <label className="ncm-label">
              {param.label}
              <span className="ncm-slider-value">{Number(value).toFixed(2)}</span>
            </label>
            <input
              type="range"
              className="ncm-slider"
              min={param.min ?? 0}
              max={param.max ?? 1}
              step={param.step ?? 0.05}
              value={value}
              onChange={(e) => handleChange(key, parseFloat(e.target.value))}
            />
            <div className="ncm-slider-labels">
              <span>{param.min ?? 0}</span>
              <span>{param.max ?? 1}</span>
            </div>
          </div>
        );

      case 'number':
        return (
          <div className="ncm-field" key={key}>
            <label className="ncm-label">{param.label}</label>
            <input
              type="number"
              className="ncm-input"
              value={value}
              min={param.min}
              max={param.max}
              onChange={(e) => handleChange(key, parseInt(e.target.value, 10))}
            />
          </div>
        );

      case 'text':
      default:
        return (
          <div className="ncm-field" key={key}>
            <label className="ncm-label">{param.label}</label>
            <input
              type="text"
              className="ncm-input"
              value={value}
              onChange={(e) => handleChange(key, e.target.value)}
            />
          </div>
        );
    }
  };

  const hasParams = config?.params && Object.keys(config.params).length > 0;

  return (
    <div className="ncm-overlay" onClick={onClose}>
      <div className="ncm-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="ncm-header">
          <div>
            <h2 className="ncm-title">{nodeName || config?.node_name || nodeId}</h2>
            <p className="ncm-description">
              {config?.description || 'Loading configuration...'}
            </p>
          </div>
          <button className="ncm-close" onClick={onClose}>✕</button>
        </div>

        {/* Body */}
        <div className="ncm-body">
          {loading && (
            <div className="ncm-loading">
              <span className="spinner" style={{ width: 28, height: 28 }} />
              <span>Loading configuration…</span>
            </div>
          )}

          {error && (
            <div className="ncm-error">{error}</div>
          )}

          {!loading && !error && !hasParams && (
            <div className="ncm-empty">
              <span style={{ fontSize: 32, opacity: 0.5 }}>⚙️</span>
              <p>This node has no configurable parameters.</p>
            </div>
          )}

          {!loading && !error && hasParams && (
            <div className="ncm-fields">
              {Object.entries(config.params).map(([key, param]) =>
                renderField(key, param)
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        {hasParams && !loading && (
          <div className="ncm-footer">
            <button className="btn btn-secondary btn-sm" onClick={onClose}>
              Cancel
            </button>
            <button
              className={`btn btn-sm ${saveSuccess ? 'ncm-btn-success' : 'btn-primary'}`}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? (
                <>
                  <span className="spinner" style={{ width: 14, height: 14, borderWidth: 2 }} />
                  Saving…
                </>
              ) : saveSuccess ? (
                '✓ Saved'
              ) : (
                'Save Changes'
              )}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
