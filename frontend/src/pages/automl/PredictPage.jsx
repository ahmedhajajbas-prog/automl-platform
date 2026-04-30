import { useState } from 'react';
import { useParams } from 'react-router-dom';
import { Zap, AlertCircle, CheckCircle, Code } from 'lucide-react';
import { predictValue } from '../../services/automlApi';  // ✅ import correct

export default function PredictPage() {
  const { runId }     = useParams();
  const [jsonInput, setJsonInput] = useState('{\n  \n}');
  const [result,    setResult]    = useState(null);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);
  const [jsonError, setJsonError] = useState(null);

  function handleJsonChange(val) {
    setJsonInput(val);
    setJsonError(null);
    try {
      JSON.parse(val);
    } catch {
      setJsonError('JSON invalide');
    }
  }

  async function handlePredict() {
    let data;
    try {
      data = JSON.parse(jsonInput);
    } catch {
      setJsonError('JSON invalide — corrigez le format');
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const r = await predictValue({ run_id: runId, data });  // ✅ corrigé
      setResult(r);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erreur de prédiction');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 680, margin: '0 auto' }}>
      {/* Header */}
      <div className="fade-up" style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.5px', marginBottom: 6 }}>
          Prédiction
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Run ID : <span style={{ fontFamily: 'monospace', color: 'var(--teal)' }}>{runId}</span>
        </p>
      </div>

      {/* JSON Editor */}
      <div className="card fade-up fade-up-1" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
          <Code size={16} color="var(--accent)" />
          <span style={{ fontWeight: 700, fontFamily: 'var(--font-display)' }}>Données d'entrée (JSON)</span>
          {jsonError && <span style={{ fontSize: 12, color: 'var(--red)', marginLeft: 'auto' }}>{jsonError}</span>}
        </div>

        <textarea
          className="form-textarea"
          style={{
            minHeight: 200,
            background: 'var(--bg-base)',
            color: 'var(--teal)',
            fontFamily: "'DM Mono', 'Fira Code', monospace",
            fontSize: 13,
            lineHeight: 1.7,
            border: jsonError ? '1px solid var(--red)' : '1px solid var(--border)',
          }}
          value={jsonInput}
          onChange={e => handleJsonChange(e.target.value)}
          spellCheck={false}
        />

        <div className="alert alert-info" style={{ marginTop: 12 }}>
          <AlertCircle size={14} style={{ flexShrink: 0 }} />
          Renseignez les mêmes colonnes que lors de l'entraînement (features uniquement, pas le target).
        </div>
      </div>

      {error && (
        <div className="alert alert-error fade-up" style={{ marginBottom: 16 }}>
          <AlertCircle size={15} style={{ flexShrink: 0 }} /> {error}
        </div>
      )}

      <button
        className="btn btn-primary btn-lg fade-up fade-up-2"
        style={{ width: '100%', marginBottom: 20 }}
        onClick={handlePredict}
        disabled={loading || !!jsonError}
      >
        {loading
          ? <><div className="spinner" /> Calcul en cours...</>
          : <><Zap size={16} /> Lancer la prédiction</>
        }
      </button>

      {/* Result */}
      {result && (
        <div
          className="fade-up"
          style={{
            padding: 28,
            background: 'linear-gradient(135deg, rgba(0,212,170,0.08), rgba(61,127,255,0.06))',
            border: '1px solid rgba(0,212,170,0.3)',
            borderRadius: 'var(--radius-xl)',
            textAlign: 'center',
          }}
        >
          <div style={{
            width: 56, height: 56,
            borderRadius: 14,
            background: 'var(--teal-dim)',
            border: '1px solid rgba(0,212,170,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 16px',
            boxShadow: '0 0 30px var(--teal-glow)',
          }}>
            <CheckCircle size={26} color="var(--teal)" />
          </div>

          <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600, marginBottom: 8, fontFamily: 'var(--font-display)' }}>
            Résultat — {result.task}
          </div>

          <div style={{
            fontSize: 'clamp(28px, 5vw, 48px)',
            fontWeight: 800,
            fontFamily: 'var(--font-display)',
            color: 'var(--teal)',
            letterSpacing: '-1px',
            marginBottom: 8,
          }}>
            {String(result.prediction)}
          </div>

          {result.confidence !== null && result.confidence !== undefined && (
            <div style={{ fontSize: 14, color: 'var(--text-secondary)' }}>
              Confiance : <strong style={{ color: 'var(--text-primary)' }}>{(result.confidence * 100).toFixed(1)}%</strong>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
