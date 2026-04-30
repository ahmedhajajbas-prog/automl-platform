import { useState, useRef, useEffect } from 'react';
import {
  Upload, Play, Download, GitMerge, CheckCircle, AlertCircle,
  AlertTriangle, ArrowRight, Clock, FileText, Zap, Shield,
  TrendingUp, Code, ChevronDown, ChevronUp, History,
} from 'lucide-react';
import {
  uploadJavaFile,
  migrateFile,
  downloadMigratedFile,
  getMigrationHistory,
  getDownloadUrl,
} from '../../services/migrationService';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const VERSIONS = ['8', '11', '17', '21'];

const VERSION_FEATURES = {
  '8':  'Lambdas, Stream API, Optional, java.time',
  '11': 'var, String.strip(), HTTP Client',
  '17': 'Records, Sealed classes, Pattern matching, Text blocks',
  '21': 'Virtual threads, Record patterns, Switch patterns',
};

const SEVERITY_COLOR = {
  critical: { bg: 'rgba(239,68,68,0.1)',   border: 'rgba(239,68,68,0.25)',   text: '#fca5a5', dot: '#ef4444' },
  high:     { bg: 'rgba(245,158,11,0.1)',  border: 'rgba(245,158,11,0.25)',  text: '#fcd34d', dot: '#f59e0b' },
  medium:   { bg: 'rgba(61,127,255,0.1)',  border: 'rgba(61,127,255,0.25)', text: '#93b4ff', dot: '#3d7fff' },
  low:      { bg: 'rgba(34,197,94,0.08)',  border: 'rgba(34,197,94,0.2)',   text: '#86efac', dot: '#22c55e' },
};

const GRADE_COLOR = { A: '#22c55e', B: '#3d7fff', C: '#f59e0b', D: '#f97316', F: '#ef4444' };

function SeverityBadge({ severity }) {
  const c = SEVERITY_COLOR[severity] || SEVERITY_COLOR.low;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      padding: '2px 9px', borderRadius: 99, fontSize: 11, fontWeight: 700,
      background: c.bg, border: `1px solid ${c.border}`, color: c.text,
      fontFamily: 'var(--font-display)', letterSpacing: '0.04em', textTransform: 'uppercase',
    }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: c.dot, flexShrink: 0 }} />
      {severity}
    </span>
  );
}

function ScoreRing({ score, grade, label }) {
  const color = GRADE_COLOR[grade] || 'var(--accent)';
  const r = 36, circ = 2 * Math.PI * r;
  const filled = (score / 100) * circ;
  return (
    <div style={{ textAlign: 'center' }}>
      <div style={{ position: 'relative', width: 96, height: 96, margin: '0 auto 8px' }}>
        <svg width="96" height="96" style={{ transform: 'rotate(-90deg)' }}>
          <circle cx="48" cy="48" r={r} fill="none" stroke="var(--bg-elevated)" strokeWidth="7" />
          <circle cx="48" cy="48" r={r} fill="none" stroke={color} strokeWidth="7"
            strokeDasharray={`${filled} ${circ}`} strokeLinecap="round"
            style={{ transition: 'stroke-dasharray 0.8s cubic-bezier(0.4,0,0.2,1)' }}
          />
        </svg>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
          <span style={{ fontSize: 22, fontWeight: 800, fontFamily: 'var(--font-display)', color, lineHeight: 1 }}>{score}</span>
          <span style={{ fontSize: 16, fontWeight: 700, color }}>{grade}</span>
        </div>
      </div>
      <div style={{ fontSize: 12, color: 'var(--text-muted)', fontWeight: 500 }}>{label}</div>
    </div>
  );
}

function IssueRow({ issue }) {
  return (
    <div style={{
      display: 'grid', gridTemplateColumns: '60px 1fr auto',
      gap: 12, padding: '12px 0', borderBottom: '1px solid var(--border)',
      alignItems: 'start',
    }}>
      <div>
        <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--text-muted)', background: 'var(--bg-elevated)', padding: '2px 6px', borderRadius: 4 }}>
          {issue.code}
        </span>
      </div>
      <div>
        <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 3 }}>{issue.title}</div>
        <div style={{ fontSize: 12, color: 'var(--text-muted)', lineHeight: 1.5 }}>{issue.description}</div>
        <div style={{ fontSize: 12, color: 'var(--teal)', marginTop: 4 }}>→ {issue.suggestion}</div>
        {issue.line > 0 && (
          <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 3 }}>Ligne {issue.line}</div>
        )}
      </div>
      <SeverityBadge severity={issue.severity} />
    </div>
  );
}

function CodeDiff({ before, after, title, explanation }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 'var(--radius)', overflow: 'hidden', marginBottom: 8 }}>
      <div
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--bg-elevated)', cursor: 'pointer' }}
        onClick={() => setOpen(!open)}
      >
        <span style={{ fontWeight: 600, fontSize: 13 }}>{title}</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{explanation?.slice(0, 60)}{explanation?.length > 60 ? '…' : ''}</span>
          {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </div>
      </div>
      {open && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0 }}>
          <div style={{ padding: 12, background: 'rgba(239,68,68,0.04)', borderRight: '1px solid var(--border)' }}>
            <div style={{ fontSize: 10, color: '#fca5a5', marginBottom: 6, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Avant</div>
            <pre style={{ fontSize: 12, color: '#fca5a5', fontFamily: 'monospace', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{before}</pre>
          </div>
          <div style={{ padding: 12, background: 'rgba(34,197,94,0.04)' }}>
            <div style={{ fontSize: 10, color: '#86efac', marginBottom: 6, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Après</div>
            <pre style={{ fontSize: 12, color: '#86efac', fontFamily: 'monospace', margin: 0, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>{after}</pre>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Étape dans le stepper ────────────────────────────────────────────────────

const STEPS = [
  { id: 1, label: 'Upload',    icon: Upload },
  { id: 2, label: 'Analyser', icon: Zap },
  { id: 3, label: 'Migrer',   icon: GitMerge },
  { id: 4, label: 'Résultats', icon: CheckCircle },
];

function StepBar({ current }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', marginBottom: 32 }}>
      {STEPS.map((s, i) => {
        const Icon = s.icon;
        const done   = s.id < current;
        const active = s.id === current;
        const color  = done ? 'var(--teal)' : active ? 'var(--accent)' : 'var(--text-muted)';
        return (
          <div key={s.id} style={{ display: 'flex', alignItems: 'center', flex: i < STEPS.length - 1 ? 1 : 'none' }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
              <div style={{
                width: 36, height: 36, borderRadius: '50%',
                background: done ? 'var(--teal-dim)' : active ? 'var(--accent-dim)' : 'var(--bg-elevated)',
                border: `2px solid ${color}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: active ? '0 0 16px var(--accent-glow)' : 'none',
                transition: 'all 0.3s',
              }}>
                {done
                  ? <CheckCircle size={16} color="var(--teal)" />
                  : <Icon size={15} color={color} />
                }
              </div>
              <span style={{ fontSize: 11, color, fontWeight: active ? 600 : 400, whiteSpace: 'nowrap' }}>{s.label}</span>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{ flex: 1, height: 2, background: done ? 'var(--teal)' : 'var(--border)', margin: '0 6px', marginBottom: 20, transition: 'background 0.3s', opacity: done ? 0.5 : 1 }} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── COMPOSANT PRINCIPAL ──────────────────────────────────────────────────────

export default function MigrationHome() {
  const fileRef = useRef();

  // State
  const [step,           setStep]          = useState(1);
  const [file,           setFile]          = useState(null);
  const [dragging,       setDragging]      = useState(false);
  const [targetVersion,  setTargetVersion] = useState('17');
  const [uploadResult,   setUploadResult]  = useState(null);
  const [migrateResult,  setMigrateResult] = useState(null);
  const [history,        setHistory]       = useState(null);
  const [loadingUpload,  setLoadingUpload] = useState(false);
  const [loadingMigrate, setLoadingMigrate] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [error,          setError]         = useState(null);
  const [showOriginal,   setShowOriginal]  = useState(false);
  const [showMigrated,   setShowMigrated]  = useState(false);
  const [activeTab,      setActiveTab]     = useState('modifications');

  // Charger l'historique au montage
  useEffect(() => {
    setLoadingHistory(true);
    getMigrationHistory()
      .then(setHistory)
      .catch(() => {})
      .finally(() => setLoadingHistory(false));
  }, []);

  function handleFile(f) {
    if (!f) return;
    if (!f.name.endsWith('.java')) {
      setError('Seuls les fichiers .java sont acceptés');
      return;
    }
    setFile(f);
    setError(null);
    setUploadResult(null);
    setMigrateResult(null);
    setStep(1);
  }

  async function handleUpload() {
    if (!file) return;
    setLoadingUpload(true);
    setError(null);
    try {
      const r = await uploadJavaFile(file);
      setUploadResult(r);
      setStep(2);
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erreur upload');
    } finally {
      setLoadingUpload(false);
    }
  }

  async function handleMigrate() {
    if (!uploadResult) return;
    setLoadingMigrate(true);
    setError(null);
    setStep(3);
    try {
      const r = await migrateFile(uploadResult.filename, targetVersion);
      setMigrateResult(r);
      setStep(4);
      // Rafraîchir l'historique
      getMigrationHistory().then(setHistory).catch(() => {});
    } catch (e) {
      setError(e?.response?.data?.detail || 'Erreur migration');
      setStep(2);
    } finally {
      setLoadingMigrate(false);
    }
  }

  function reset() {
    setStep(1); setFile(null); setUploadResult(null); setMigrateResult(null); setError(null);
    setShowOriginal(false); setShowMigrated(false);
  }

  const res       = migrateResult;
  const sb        = res?.score_before;
  const sa        = res?.score_after;
  const imp       = res?.improvement;
  const abIssues  = res?.analysis_before?.issues || [];
  const aaIssues  = res?.analysis_after?.issues  || [];

  return (
    <div className="page-content page-enter" style={{ paddingTop: 32, paddingBottom: 64, maxWidth: 960 }}>

      {/* Header */}
      <div className="fade-up" style={{ marginBottom: 32 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: 7, padding: '4px 12px', background: 'var(--teal-dim)', border: '1px solid rgba(0,212,170,0.25)', borderRadius: 99, fontSize: 11, color: 'var(--teal)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 12, fontFamily: 'var(--font-display)' }}>
              <GitMerge size={11} /> Migration Java
            </div>
            <h1 style={{ fontSize: 30, fontWeight: 800, letterSpacing: '-1px', marginBottom: 6 }}>
              Migration de code Java
            </h1>
            <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
              Uploadez un fichier <code style={{ background: 'var(--bg-elevated)', padding: '1px 6px', borderRadius: 4, fontSize: 13 }}>.java</code>, choisissez la version cible, et le LLM migre + corrige automatiquement.
            </p>
          </div>

          {/* Historique pill */}
          {history?.count > 0 && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', flexShrink: 0 }}>
              <History size={14} color="var(--text-muted)" />
              <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{history.count} fichier{history.count > 1 ? 's' : ''} migré{history.count > 1 ? 's' : ''}</span>
            </div>
          )}
        </div>
      </div>

      {/* Stepper */}
      <div className="fade-up fade-up-1">
        <StepBar current={step} />
      </div>

      {/* ── ÉTAPE 1 : Upload ── */}
      {step <= 2 && (
        <div className="fade-up fade-up-2" style={{ marginBottom: 20 }}>
          {/* Drop zone */}
          <div
            className={`drop-zone ${dragging ? 'dragging' : ''}`}
            style={{ marginBottom: 20 }}
            onClick={() => !uploadResult && fileRef.current.click()}
            onDragOver={e => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={e => { e.preventDefault(); setDragging(false); handleFile(e.dataTransfer.files[0]); }}
          >
            <input ref={fileRef} type="file" accept=".java" style={{ display: 'none' }} onChange={e => handleFile(e.target.files[0])} />
            <div style={{ position: 'relative', zIndex: 1 }}>
              {file ? (
                <>
                  <div style={{ width: 56, height: 56, borderRadius: 14, background: 'var(--teal-dim)', border: '1px solid rgba(0,212,170,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 14px', boxShadow: '0 0 28px var(--teal-glow)' }}>
                    <FileText size={26} color="var(--teal)" />
                  </div>
                  <div style={{ fontWeight: 700, fontSize: 16, marginBottom: 4 }}>{file.name}</div>
                  <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>{(file.size / 1024).toFixed(1)} KB</div>
                  {!uploadResult && (
                    <div style={{ marginTop: 10, fontSize: 13, color: 'var(--text-muted)', cursor: 'pointer' }} onClick={e => { e.stopPropagation(); setFile(null); }}>
                      Changer de fichier
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="drop-zone-icon"><Upload size={26} color="var(--accent)" /></div>
                  <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 8 }}>Glissez votre fichier .java ici</div>
                  <div style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 12 }}>ou cliquez pour parcourir</div>
                  <span className="chip">.java</span>
                </>
              )}
            </div>
          </div>

          {/* Upload success */}
          {uploadResult && (
            <div className="alert alert-success" style={{ marginBottom: 16 }}>
              <CheckCircle size={15} style={{ flexShrink: 0 }} />
              <span><strong>{uploadResult.filename}</strong> uploadé — {(uploadResult.size_bytes / 1024).toFixed(1)} KB</span>
            </div>
          )}

          {error && (
            <div className="alert alert-error" style={{ marginBottom: 16 }}>
              <AlertCircle size={15} style={{ flexShrink: 0 }} /> {error}
            </div>
          )}

          {/* Upload button */}
          {file && !uploadResult && (
            <button className="btn btn-primary btn-lg" style={{ width: '100%', marginBottom: 16 }} onClick={handleUpload} disabled={loadingUpload}>
              {loadingUpload ? <><div className="spinner" /> Upload en cours...</> : <><Upload size={15} /> Uploader le fichier</>}
            </button>
          )}

          {/* Config migration */}
          {uploadResult && (
            <div className="card">
              <div style={{ fontWeight: 700, fontFamily: 'var(--font-display)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Zap size={16} color="var(--teal)" /> Configuration de la migration
              </div>

              <div className="form-group" style={{ marginBottom: 20 }}>
                <label className="form-label">Version Java cible</label>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                  {VERSIONS.map(v => (
                    <div
                      key={v}
                      onClick={() => setTargetVersion(v)}
                      style={{
                        padding: '12px 8px', borderRadius: 'var(--radius)', textAlign: 'center', cursor: 'pointer',
                        background: targetVersion === v ? 'var(--teal-dim)' : 'var(--bg-elevated)',
                        border: `1.5px solid ${targetVersion === v ? 'var(--teal)' : 'var(--border)'}`,
                        transition: 'all 0.2s',
                        boxShadow: targetVersion === v ? '0 0 16px var(--teal-glow)' : 'none',
                      }}
                    >
                      <div style={{ fontWeight: 800, fontSize: 18, fontFamily: 'var(--font-display)', color: targetVersion === v ? 'var(--teal)' : 'var(--text-primary)' }}>
                        {v}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4 }}>
                        {VERSION_FEATURES[v].split(',')[0]}
                      </div>
                    </div>
                  ))}
                </div>
                <div className="alert alert-info" style={{ marginTop: 10 }}>
                  <Zap size={13} style={{ flexShrink: 0 }} />
                  Java {targetVersion} — {VERSION_FEATURES[targetVersion]}
                </div>
              </div>

              <button
                className="btn btn-lg"
                style={{ width: '100%', background: 'linear-gradient(135deg, var(--teal), var(--accent))', color: 'white', boxShadow: '0 0 24px var(--teal-glow)', border: 'none' }}
                onClick={handleMigrate}
                disabled={loadingMigrate}
              >
                {loadingMigrate
                  ? <><div className="spinner" /> Migration LLM en cours (GPT-4o)...</>
                  : <><Play size={16} /> Lancer la migration vers Java {targetVersion}</>
                }
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── ÉTAPE 3 : Loading ── */}
      {step === 3 && loadingMigrate && (
        <div className="card fade-up" style={{ textAlign: 'center', padding: 52 }}>
          <div style={{ width: 64, height: 64, margin: '0 auto 20px', borderRadius: '50%', background: 'var(--teal-dim)', border: '1px solid rgba(0,212,170,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', animation: 'pulse-glow 2s infinite' }}>
            <GitMerge size={28} color="var(--teal)" />
          </div>
          <h3 style={{ marginBottom: 8, fontSize: 20 }}>Migration en cours…</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, maxWidth: 400, margin: '0 auto' }}>
            GPT-4o analyse le code, corrige les problèmes détectés et migre vers Java {targetVersion}
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 24, marginTop: 28 }}>
            {['Analyse statique', 'Appel LLM', 'Score qualité'].map((s, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: 'var(--text-muted)' }}>
                <div className="spinner" style={{ width: 12, height: 12, borderWidth: 2 }} />
                {s}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── ÉTAPE 4 : Résultats ── */}
      {step === 4 && res && (
        <div className="fade-up">

          {/* Scores */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ fontWeight: 700, fontFamily: 'var(--font-display)', marginBottom: 20, display: 'flex', alignItems: 'center', gap: 8 }}>
              <TrendingUp size={16} color="var(--teal)" /> Score qualité
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr auto 1fr', gap: 16, alignItems: 'center' }}>
              <ScoreRing score={sb?.score ?? 0} grade={sb?.grade ?? '?'} label="Avant migration" />

              {/* Delta */}
              <div style={{ textAlign: 'center', padding: '0 16px' }}>
                <div style={{
                  fontSize: 28, fontWeight: 800, fontFamily: 'var(--font-display)',
                  color: imp?.improved ? 'var(--teal)' : 'var(--red)',
                }}>
                  {imp?.label || '—'}
                </div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                  {imp?.issues_fixed > 0 && <div style={{ color: 'var(--green)' }}>✓ {imp.issues_fixed} problème{imp.issues_fixed > 1 ? 's' : ''} corrigé{imp.issues_fixed > 1 ? 's' : ''}</div>}
                </div>
                <ArrowRight size={20} color="var(--text-muted)" style={{ marginTop: 8 }} />
              </div>

              <ScoreRing score={sa?.score ?? 0} grade={sa?.grade ?? '?'} label="Après migration" />
            </div>

            {/* Risk levels */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 20 }}>
              {[
                { label: 'Risque avant', val: imp?.risk_before, color: 'var(--red)' },
                { label: 'Risque après', val: imp?.risk_after,  color: 'var(--green)' },
              ].map((r, i) => (
                <div key={i} style={{ padding: '10px 14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius)', textAlign: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600, marginBottom: 4 }}>{r.label}</div>
                  <div style={{ fontWeight: 700, color: r.color, fontFamily: 'var(--font-display)', textTransform: 'capitalize' }}>{r.val}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Summary */}
          {res.summary && (
            <div className="alert alert-success fade-up" style={{ marginBottom: 20 }}>
              <CheckCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
              <div>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>Résumé de la migration</div>
                <div style={{ fontSize: 13, lineHeight: 1.6 }}>{res.summary}</div>
              </div>
            </div>
          )}

          {/* Tabs */}
          <div style={{ display: 'flex', gap: 4, marginBottom: 16, background: 'var(--bg-elevated)', padding: 4, borderRadius: 'var(--radius)', width: 'fit-content' }}>
            {[
              { id: 'modifications', label: `Modifications (${res.modifications?.length ?? 0})`, icon: Code },
              { id: 'issues_before', label: `Problèmes avant (${abIssues.length})`, icon: AlertTriangle },
              { id: 'issues_after',  label: `Problèmes après (${aaIssues.length})`, icon: Shield },
            ].map(t => {
              const Icon = t.icon;
              return (
                <button
                  key={t.id}
                  onClick={() => setActiveTab(t.id)}
                  className="btn btn-sm"
                  style={{
                    background: activeTab === t.id ? 'var(--bg-card)' : 'transparent',
                    color: activeTab === t.id ? 'var(--text-primary)' : 'var(--text-muted)',
                    border: activeTab === t.id ? '1px solid var(--border)' : '1px solid transparent',
                    gap: 6,
                  }}
                >
                  <Icon size={13} /> {t.label}
                </button>
              );
            })}
          </div>

          {/* Tab content */}
          <div className="card" style={{ marginBottom: 20 }}>
            {activeTab === 'modifications' && (
              res.modifications?.length > 0
                ? res.modifications.map((m, i) => <CodeDiff key={i} {...m} />)
                : <div className="empty-state"><p style={{ color: 'var(--text-muted)' }}>Aucune modification listée</p></div>
            )}
            {activeTab === 'issues_before' && (
              abIssues.length > 0
                ? abIssues.map((issue, i) => <IssueRow key={i} issue={issue} />)
                : <div className="empty-state" style={{ padding: 32, textAlign: 'center', color: 'var(--text-muted)' }}>✓ Aucun problème détecté</div>
            )}
            {activeTab === 'issues_after' && (
              aaIssues.length > 0
                ? aaIssues.map((issue, i) => <IssueRow key={i} issue={issue} />)
                : <div style={{ textAlign: 'center', padding: 32 }}>
                    <CheckCircle size={32} color="var(--teal)" style={{ marginBottom: 8 }} />
                    <div style={{ color: 'var(--teal)', fontWeight: 600 }}>Aucun problème détecté dans le code migré !</div>
                  </div>
            )}
          </div>

          {/* Code viewers */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ display: 'flex', gap: 10, marginBottom: 16 }}>
              <button className={`btn btn-sm ${showOriginal ? 'btn-secondary' : ''}`} style={{ color: showOriginal ? 'var(--text-primary)' : 'var(--text-muted)' }} onClick={() => setShowOriginal(!showOriginal)}>
                <Code size={13} /> Code original {showOriginal ? '↑' : '↓'}
              </button>
              <button className={`btn btn-sm ${showMigrated ? 'btn-teal' : ''}`} style={{ color: showMigrated ? 'var(--teal)' : 'var(--text-muted)' }} onClick={() => setShowMigrated(!showMigrated)}>
                <GitMerge size={13} /> Code migré {showMigrated ? '↑' : '↓'}
              </button>
            </div>

            {showOriginal && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600 }}>Code original</div>
                <pre className="code-block" style={{ color: 'var(--text-secondary)', maxHeight: 320, overflow: 'auto' }}>{res.original_code}</pre>
              </div>
            )}
            {showMigrated && (
              <div>
                <div style={{ fontSize: 11, color: 'var(--teal)', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600 }}>Code migré — Java {targetVersion}</div>
                <pre className="code-block" style={{ maxHeight: 320, overflow: 'auto' }}>{res.migrated_code}</pre>
              </div>
            )}
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', gap: 12 }}>
            <button
              className="btn btn-teal btn-lg"
              style={{ flex: 1 }}
              onClick={() => downloadMigratedFile(res.filename)}
            >
              <Download size={16} /> Télécharger le code migré (.java)
            </button>
            <button className="btn btn-secondary btn-lg" onClick={reset}>
              Nouvelle migration
            </button>
          </div>
        </div>
      )}

      {/* ── Historique ── */}
      {history?.count > 0 && step <= 2 && (
        <div className="card fade-up fade-up-4" style={{ marginTop: 32 }}>
          <div style={{ fontWeight: 700, fontFamily: 'var(--font-display)', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
            <History size={15} color="var(--text-secondary)" /> Migrations précédentes
          </div>
          {history.files.map((f, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 0', borderBottom: i < history.files.length - 1 ? '1px solid var(--border)' : 'none' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <FileText size={15} color="var(--teal)" />
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>{f.filename}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{(f.size_bytes / 1024).toFixed(1)} KB</div>
                </div>
              </div>
              <a href={f.download_url} download style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }} className="btn btn-sm btn-teal">
                <Download size={12} /> Télécharger
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
