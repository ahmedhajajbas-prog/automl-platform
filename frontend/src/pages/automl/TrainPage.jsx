import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Brain, Play, Settings, BarChart2, Zap, Trophy, ArrowRight, AlertCircle, CheckCircle, TrendingUp } from 'lucide-react';
import { analyzeFeatures, trainModel } from '../../services/automlApi';

function QualityBadge({ quality }) {
  const map = { excellent: 'badge-excellent', good: 'badge-good', weak: 'badge-weak', poor: 'badge-poor' };
  return <span className={`badge ${map[quality] || 'badge-poor'}`}>{quality}</span>;
}

function MetricCell({ value, suffix = '' }) {
  if (value === null || value === undefined) return <span style={{ color: 'var(--text-muted)' }}>—</span>;
  return <span style={{ fontFamily: 'monospace', fontWeight: 600 }}>{typeof value === 'number' ? value.toFixed(4) : value}{suffix}</span>;
}

export default function TrainPage() {
  const { runId }    = useParams();
  const navigate     = useNavigate();

  // Config state
  const [target,     setTarget]     = useState('');
  const [featureStr, setFeatureStr] = useState('');
  const [task,       setTask]       = useState('auto');
  const [testSize,   setTestSize]   = useState(0.2);
  const [cvFolds,    setCvFolds]    = useState(5);
  const [useOptuna,  setUseOptuna]  = useState(true);
  const [optunaTrials, setOptunaTrials] = useState(40);

  // UI state
  const [analysisResult, setAnalysisResult] = useState(null);
  const [trainResult,    setTrainResult]    = useState(null);
  const [loadingAnalysis, setLoadingAnalysis] = useState(false);
  const [loadingTrain,   setLoadingTrain]   = useState(false);
  const [error,          setError]          = useState(null);

  const features = featureStr.split(',').map(s => s.trim()).filter(Boolean);

  async function handleAnalyze() {
    if (!target || features.length === 0) {
      setError('Renseignez le target et au moins une feature');
      return;
    }
    setLoadingAnalysis(true);
    setError(null);
    try {
      const r = await analyzeFeatures({ run_id: runId, target, features });
      setAnalysisResult(r);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erreur analyse');
    } finally {
      setLoadingAnalysis(false);
    }
  }

  async function handleTrain() {
    if (!target || features.length === 0) {
      setError('Renseignez le target et les features');
      return;
    }
    setLoadingTrain(true);
    setError(null);
    try {
      const r = await trainModel({
        run_id: runId,
        target,
        features,
        task,
        test_size: parseFloat(testSize),
        cv_folds: parseInt(cvFolds),
        use_optuna: useOptuna,
        optuna_trials: parseInt(optunaTrials),
      });
      setTrainResult(r);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erreur entraînement');
    } finally {
      setLoadingTrain(false);
    }
  }

  return (
    <div style={{ maxWidth: 860 }}>
      {/* Header */}
      <div className="fade-up" style={{ marginBottom: 28 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.5px', marginBottom: 6 }}>
          Entraînement des modèles
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Run ID : <span style={{ fontFamily: 'monospace', color: 'var(--teal)' }}>{runId}</span>
        </p>
      </div>

      {/* ── Section 1: Config ── */}
      <div className="card fade-up fade-up-1" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
          <div style={{ width: 32, height: 32, borderRadius: 8, background: 'var(--accent-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(61,127,255,0.25)' }}>
            <Settings size={16} color="var(--accent)" />
          </div>
          <span style={{ fontWeight: 700, fontFamily: 'var(--font-display)', fontSize: 16 }}>Configuration</span>
        </div>

        <div className="grid-2" style={{ gap: 16, marginBottom: 16 }}>
          <div className="form-group">
            <label className="form-label">Colonne cible (target) *</label>
            <input className="form-input" placeholder="ex: price, survived, churn" value={target} onChange={e => setTarget(e.target.value)} />
          </div>
          <div className="form-group">
            <label className="form-label">Type de tâche</label>
            <select className="form-select" value={task} onChange={e => setTask(e.target.value)}>
              <option value="auto">Auto-détection</option>
              <option value="classification">Classification</option>
              <option value="regression">Régression</option>
            </select>
          </div>
        </div>

        <div className="form-group" style={{ marginBottom: 16 }}>
          <label className="form-label">Features (séparées par des virgules) *</label>
          <input className="form-input" placeholder="col1, col2, col3, ..." value={featureStr} onChange={e => setFeatureStr(e.target.value)} />
          {features.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginTop: 8 }}>
              {features.map(f => <span key={f} className="chip selected">{f}</span>)}
            </div>
          )}
        </div>

        <div className="grid-2" style={{ gap: 16, marginBottom: 16 }}>
          <div className="form-group">
            <label className="form-label">Test size</label>
            <select className="form-select" value={testSize} onChange={e => setTestSize(e.target.value)}>
              {[0.1, 0.15, 0.2, 0.25, 0.3].map(v => (
                <option key={v} value={v}>{Math.round(v * 100)}%</option>
              ))}
            </select>
          </div>
          <div className="form-group">
            <label className="form-label">CV Folds</label>
            <select className="form-select" value={cvFolds} onChange={e => setCvFolds(e.target.value)}>
              {[3, 5, 7, 10].map(v => <option key={v} value={v}>{v} folds</option>)}
            </select>
          </div>
        </div>

        {/* Optuna toggle */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '14px 16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
              <Zap size={15} color="var(--amber)" /> Optuna Hyperparameter Tuning
            </div>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 3 }}>
              Recherche bayésienne des meilleurs hyperparamètres
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {useOptuna && (
              <input
                type="number"
                className="form-input"
                style={{ width: 80 }}
                value={optunaTrials}
                min={10} max={200}
                onChange={e => setOptunaTrials(e.target.value)}
              />
            )}
            <div
              onClick={() => setUseOptuna(!useOptuna)}
              style={{
                width: 44, height: 24, borderRadius: 99,
                background: useOptuna ? 'var(--accent)' : 'var(--bg-hover)',
                cursor: 'pointer', transition: 'var(--transition)',
                position: 'relative', flexShrink: 0,
                boxShadow: useOptuna ? '0 0 12px var(--accent-glow)' : 'none',
              }}
            >
              <div style={{
                width: 18, height: 18, borderRadius: '50%', background: 'white',
                position: 'absolute', top: 3,
                left: useOptuna ? 23 : 3,
                transition: 'var(--transition)',
              }} />
            </div>
          </div>
        </div>

        {/* Analyze button */}
        <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>
          <button className="btn btn-secondary" onClick={handleAnalyze} disabled={loadingAnalysis || !target || features.length === 0}>
            {loadingAnalysis ? <><div className="spinner" /> Analyse...</> : <><BarChart2 size={15} /> Analyser les features</>}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="alert alert-error fade-up" style={{ marginBottom: 16 }}>
          <AlertCircle size={15} style={{ flexShrink: 0 }} /> {error}
        </div>
      )}

      {/* ── Section 2: Feature Analysis ── */}
      {analysisResult && (
        <div className="card fade-up" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <div style={{ width: 32, height: 32, borderRadius: 8, background: 'var(--teal-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px solid rgba(0,212,170,0.25)' }}>
              <TrendingUp size={16} color="var(--teal)" />
            </div>
            <span style={{ fontWeight: 700, fontFamily: 'var(--font-display)', fontSize: 16 }}>Analyse des features</span>
            <span style={{ fontSize: 12, padding: '2px 8px', background: 'var(--teal-dim)', color: 'var(--teal)', borderRadius: 99, border: '1px solid rgba(0,212,170,0.2)' }}>
              Tâche détectée : {analysisResult.task_detected}
            </span>
          </div>

          {analysisResult.feature_analysis?.warnings?.map((w, i) => (
            <div key={i} className="alert alert-warning" style={{ marginBottom: 8 }}>
              <AlertCircle size={14} style={{ flexShrink: 0 }} /> {w}
            </div>
          ))}

          {analysisResult.feature_analysis?.recommended_features?.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600 }}>Features recommandées</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                {analysisResult.feature_analysis.recommended_features.map(f => (
                  <div key={f.feature} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '5px 12px', background: 'var(--green-dim)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 8, fontSize: 13 }}>
                    <span style={{ color: 'var(--green)', fontWeight: 600 }}>{f.feature}</span>
                    <span style={{ color: 'var(--text-muted)' }}>r={f.correlation}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {analysisResult.imbalance_info?.imbalanced && (
            <div className="alert alert-warning">
              <AlertCircle size={14} style={{ flexShrink: 0 }} />
              Classes déséquilibrées (ratio {analysisResult.imbalance_info.ratio}x) · {analysisResult.imbalance_info.recommendation}
            </div>
          )}

          {/* Launch train */}
          <button
            className="btn btn-primary btn-lg"
            style={{ width: '100%', marginTop: 16 }}
            onClick={handleTrain}
            disabled={loadingTrain}
          >
            {loadingTrain
              ? <><div className="spinner" /> Entraînement en cours{useOptuna ? ' (Optuna actif)' : ''}...</>
              : <><Play size={16} /> Lancer l'entraînement</>
            }
          </button>
        </div>
      )}

      {/* ── Section 3: Results ── */}
      {trainResult && (
        <div className="fade-up">
          {/* Best model */}
          <div style={{
            padding: '20px 24px',
            background: 'linear-gradient(135deg, rgba(61,127,255,0.1), rgba(0,212,170,0.08))',
            border: '1px solid rgba(61,127,255,0.25)',
            borderRadius: 'var(--radius-lg)',
            marginBottom: 20,
            display: 'flex',
            alignItems: 'center',
            gap: 16,
          }}>
            <div style={{ width: 48, height: 48, borderRadius: 12, background: 'var(--accent-dim)', border: '1px solid rgba(61,127,255,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: '0 0 24px var(--accent-glow)' }}>
              <Trophy size={22} color="var(--accent)" />
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, fontFamily: 'var(--font-display)' }}>Meilleur modèle</div>
              <div style={{ fontSize: 22, fontWeight: 800, fontFamily: 'var(--font-display)', marginTop: 2 }}>{trainResult.best_model?.name}</div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <QualityBadge quality={trainResult.best_model?.quality} />
              {trainResult.optuna_used && (
                <div style={{ fontSize: 11, color: 'var(--amber)', marginTop: 4, display: 'flex', alignItems: 'center', gap: 4, justifyContent: 'flex-end' }}>
                  <Zap size={11} /> Optuna optimisé
                </div>
              )}
            </div>
          </div>

          {/* Recommendation */}
          {trainResult.recommendation && (
            <div className="alert alert-info" style={{ marginBottom: 20 }}>
              <CheckCircle size={15} style={{ flexShrink: 0 }} />
              {trainResult.recommendation}
            </div>
          )}

          {/* Leaderboard */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ fontWeight: 700, fontFamily: 'var(--font-display)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
              <BarChart2 size={16} color="var(--accent)" /> Leaderboard
            </div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Modèle</th>
                    {trainResult.task === 'classification' ? (
                      <><th>F1 (weighted)</th><th>Accuracy</th><th>CV F1</th><th>ROC-AUC</th></>
                    ) : (
                      <><th>R²</th><th>RMSE</th><th>MAE</th><th>CV RMSE</th></>
                    )}
                    <th>Temps</th>
                    <th>Qualité</th>
                  </tr>
                </thead>
                <tbody>
                  {trainResult.leaderboard?.map((m, i) => (
                    <tr key={i} style={i === 0 ? { background: 'rgba(61,127,255,0.04)' } : {}}>
                      <td style={{ color: i === 0 ? 'var(--accent)' : 'var(--text-muted)', fontWeight: i === 0 ? 700 : 400 }}>{i + 1}</td>
                      <td className={`td-model ${i === 0 ? 'td-best' : ''}`}>{m.model}</td>
                      {trainResult.task === 'classification' ? (
                        <><td><MetricCell value={m.f1_weighted} /></td><td><MetricCell value={m.accuracy} /></td><td><MetricCell value={m.cv_f1_weighted} /></td><td><MetricCell value={m.roc_auc} /></td></>
                      ) : (
                        <><td><MetricCell value={m.r2} /></td><td><MetricCell value={m.rmse} /></td><td><MetricCell value={m.mae} /></td><td><MetricCell value={m.cv_rmse} /></td></>
                      )}
                      <td style={{ color: 'var(--text-muted)', fontSize: 13 }}>{m.training_time_sec}s</td>
                      <td><QualityBadge quality={m.model_quality} /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Feature importance */}
          {trainResult.feature_importance?.available && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div style={{ fontWeight: 700, fontFamily: 'var(--font-display)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Brain size={16} color="var(--purple)" /> Feature Importance
              </div>
              {trainResult.feature_importance.items?.slice(0, 10).map((item, i) => {
                const maxImp = trainResult.feature_importance.items[0]?.importance || 1;
                const pct = (item.importance / maxImp * 100).toFixed(1);
                return (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                    <div style={{ width: 130, fontSize: 13, fontFamily: 'monospace', color: 'var(--text-secondary)', flexShrink: 0, overflow: 'hidden', textOverflow: 'ellipsis' }}>{item.feature}</div>
                    <div style={{ flex: 1 }}>
                      <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${pct}%`, background: `linear-gradient(90deg, var(--purple), var(--accent))` }} />
                      </div>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', width: 60, textAlign: 'right', fontFamily: 'monospace' }}>{item.importance.toFixed(4)}</div>
                  </div>
                );
              })}
            </div>
          )}

          {/* SHAP */}
          {trainResult.shap_summary?.available && (
            <div className="card" style={{ marginBottom: 20 }}>
              <div style={{ fontWeight: 700, fontFamily: 'var(--font-display)', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Zap size={16} color="var(--teal)" /> SHAP — Impact réel des features
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-muted)', marginBottom: 16 }}>Valeurs SHAP moyennes absolues (impact sur les prédictions)</div>
              {trainResult.shap_summary.values?.slice(0, 8).map((item, i) => {
                const maxVal = trainResult.shap_summary.values[0]?.shap_importance || 1;
                const pct = (item.shap_importance / maxVal * 100).toFixed(1);
                return (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 10 }}>
                    <div style={{ width: 130, fontSize: 13, fontFamily: 'monospace', color: 'var(--text-secondary)', flexShrink: 0 }}>{item.feature}</div>
                    <div style={{ flex: 1 }}>
                      <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${pct}%`, background: `linear-gradient(90deg, var(--teal), var(--accent))` }} />
                      </div>
                    </div>
                    <div style={{ fontSize: 12, color: 'var(--text-muted)', width: 60, textAlign: 'right', fontFamily: 'monospace' }}>{item.shap_importance.toFixed(4)}</div>
                  </div>
                );
              })}
            </div>
          )}

          <button
            className="btn btn-primary btn-lg"
            style={{ width: '100%' }}
            onClick={() => navigate(`/automl/predict/${runId}`)}
          >
            Aller aux prédictions <ArrowRight size={16} />
          </button>
        </div>
      )}

      {/* Train button if no analysis yet */}
      {!analysisResult && !trainResult && (
        <div className="card" style={{ textAlign: 'center', padding: 40 }}>
          <div className="empty-state-icon" style={{ margin: '0 auto 16px' }}>
            <Brain size={22} color="var(--text-muted)" />
          </div>
          <p style={{ color: 'var(--text-muted)', fontSize: 14 }}>
            Renseignez le target et les features, puis lancez l'analyse
          </p>
        </div>
      )}
    </div>
  );
}
