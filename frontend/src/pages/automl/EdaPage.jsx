import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { BarChart2, AlertTriangle, Copy, Layers, Hash, TrendingUp, ArrowRight } from 'lucide-react';
import { getEda } from '../../services/automlApi';

function MissingBar({ col, count, total }) {
  const pct = total > 0 ? (count / total * 100) : 0;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
      <div style={{ width: 140, fontSize: 13, color: 'var(--text-secondary)', flexShrink: 0, fontFamily: 'monospace' }}>{col}</div>
      <div style={{ flex: 1 }}>
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${Math.max(pct, pct > 0 ? 2 : 0)}%`, background: pct > 20 ? 'var(--red)' : pct > 5 ? 'var(--amber)' : 'var(--teal)' }} />
        </div>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', width: 60, textAlign: 'right' }}>{pct.toFixed(1)}%</div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', width: 40, textAlign: 'right' }}>{count}</div>
    </div>
  );
}

export default function EdaPage() {
  const { runId }    = useParams();
  const navigate     = useNavigate();
  const [eda,  setEda]  = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getEda(runId)
      .then(setEda)
      .catch(e => setError(e?.response?.data?.detail || 'Erreur EDA'))
      .finally(() => setLoading(false));
  }, [runId]);

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--text-secondary)', padding: 40 }}>
      <div className="spinner" /> Analyse en cours...
    </div>
  );

  if (error) return (
    <div className="alert alert-error">{error}</div>
  );

  if (!eda) return null;

  const missingCols = Object.entries(eda.missing_by_column || {}).filter(([, v]) => v > 0);
  const totalRows   = eda.shape?.rows || 1;

  return (
    <div style={{ maxWidth: 860 }}>
      {/* Header */}
      <div className="fade-up" style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.5px', marginBottom: 6 }}>
          Exploratory Data Analysis
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Run ID : <span style={{ fontFamily: 'monospace', color: 'var(--teal)' }}>{runId}</span>
        </p>
      </div>

      {/* Stats row */}
      <div className="grid-4 fade-up fade-up-1" style={{ marginBottom: 24 }}>
        {[
          { icon: Layers,    val: eda.shape?.rows?.toLocaleString(),    label: 'Lignes',         color: 'var(--accent)' },
          { icon: Hash,      val: eda.shape?.columns,                   label: 'Colonnes',       color: 'var(--teal)' },
          { icon: AlertTriangle, val: eda.missing_total,                label: 'Valeurs manq.', color: eda.missing_total > 0 ? 'var(--amber)' : 'var(--green)' },
          { icon: Copy,      val: eda.duplicate_rows,                   label: 'Doublons',       color: eda.duplicate_rows > 0 ? 'var(--red)' : 'var(--green)' },
        ].map(({ icon: Icon, val, label, color }, i) => (
          <div key={i} className="stat-card">
            <div className="stat-icon" style={{ background: `${color}18`, border: `1px solid ${color}30` }}>
              <Icon size={16} color={color} />
            </div>
            <div className="stat-value" style={{ color }}>{val}</div>
            <div className="stat-label">{label}</div>
          </div>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 20 }}>
        {/* Numeric cols */}
        <div className="card fade-up fade-up-2">
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: '0.07em', fontFamily: 'var(--font-display)', marginBottom: 12 }}>
            Colonnes numériques ({eda.numeric_columns?.length})
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {eda.numeric_columns?.map(c => <span key={c} className="chip" style={{ borderColor: 'rgba(61,127,255,0.25)', color: 'var(--accent)' }}>{c}</span>)}
            {!eda.numeric_columns?.length && <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>Aucune</span>}
          </div>
        </div>

        {/* Categorical cols */}
        <div className="card fade-up fade-up-2">
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--teal)', textTransform: 'uppercase', letterSpacing: '0.07em', fontFamily: 'var(--font-display)', marginBottom: 12 }}>
            Colonnes catégorielles ({eda.categorical_columns?.length})
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {eda.categorical_columns?.map(c => <span key={c} className="chip" style={{ borderColor: 'rgba(0,212,170,0.25)', color: 'var(--teal)' }}>{c}</span>)}
            {!eda.categorical_columns?.length && <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>Aucune</span>}
          </div>
        </div>
      </div>

      {/* Outliers */}
      {eda.outliers?.length > 0 && (
        <div className="card fade-up fade-up-3" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <AlertTriangle size={16} color="var(--amber)" />
            <span style={{ fontWeight: 600, fontFamily: 'var(--font-display)' }}>Outliers détectés</span>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {eda.outliers.map((o, i) => (
              <div key={i} style={{ padding: '6px 12px', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 8, fontSize: 13 }}>
                <span style={{ color: 'var(--amber)', fontWeight: 600 }}>{o.column}</span>
                <span style={{ color: 'var(--text-muted)', marginLeft: 8 }}>IQR: {o.iqr_outliers} · Z: {o.zscore_outliers} ({o.pct}%)</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Missing values */}
      {missingCols.length > 0 && (
        <div className="card fade-up fade-up-3" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <TrendingUp size={16} color="var(--text-secondary)" />
            <span style={{ fontWeight: 600, fontFamily: 'var(--font-display)' }}>Valeurs manquantes par colonne</span>
          </div>
          {missingCols.map(([col, count]) => (
            <MissingBar key={col} col={col} count={count} total={totalRows} />
          ))}
        </div>
      )}

      {/* Constant / high cardinality warnings */}
      {(eda.constant_columns?.length > 0 || eda.high_cardinality_columns?.length > 0) && (
        <div className="fade-up fade-up-4" style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 20 }}>
          {eda.constant_columns?.length > 0 && (
            <div className="alert alert-warning">
              <AlertTriangle size={15} style={{ flexShrink: 0 }} />
              Colonnes constantes (à supprimer) : {eda.constant_columns.join(', ')}
            </div>
          )}
          {eda.high_cardinality_columns?.length > 0 && (
            <div className="alert alert-info">
              <BarChart2 size={15} style={{ flexShrink: 0 }} />
              Haute cardinalité ({'>'}50 valeurs uniques) : {eda.high_cardinality_columns.join(', ')}
            </div>
          )}
        </div>
      )}

      {/* Sample rows */}
      <div className="card fade-up fade-up-4" style={{ marginBottom: 28 }}>
        <div style={{ fontWeight: 600, fontFamily: 'var(--font-display)', marginBottom: 14 }}>
          Aperçu — 5 premières lignes
        </div>
        <div style={{ overflowX: 'auto' }}>
          {eda.sample_rows?.length > 0 && (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border)' }}>
                  {Object.keys(eda.sample_rows[0]).map(col => (
                    <th key={col} style={{ padding: '8px 12px', textAlign: 'left', color: 'var(--text-muted)', fontWeight: 600, whiteSpace: 'nowrap', fontSize: 12, letterSpacing: '0.05em', textTransform: 'uppercase', fontFamily: 'var(--font-display)' }}>
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {eda.sample_rows.map((row, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid var(--border)' }}>
                    {Object.values(row).map((v, j) => (
                      <td key={j} style={{ padding: '8px 12px', color: 'var(--text-secondary)', whiteSpace: 'nowrap', maxWidth: 150, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {v === null || v === undefined ? <span style={{ color: 'var(--text-muted)' }}>null</span> : String(v)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <button
        className="btn btn-primary btn-lg"
        style={{ width: '100%' }}
        onClick={() => navigate(`/automl/train/${runId}`)}
      >
        Continuer vers l'entraînement <ArrowRight size={16} />
      </button>
    </div>
  );
}
