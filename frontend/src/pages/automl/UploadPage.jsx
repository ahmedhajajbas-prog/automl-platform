import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, FileText, CheckCircle, AlertCircle, Table, Hash, Layers } from 'lucide-react';
import { uploadDataset } from '../../services/automlApi';

export default function UploadPage() {
  const navigate  = useNavigate();
  const fileRef   = useRef();
  const [dragging, setDragging] = useState(false);
  const [file,     setFile]     = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [result,   setResult]   = useState(null);
  const [error,    setError]    = useState(null);

  function handleFile(f) {
    if (!f) return;
    const ext = f.name.split('.').pop().toLowerCase();
    if (!['csv', 'xlsx', 'xls'].includes(ext)) {
      setError('Format non supporté. Utilisez CSV ou Excel (.xlsx/.xls)');
      return;
    }
    setFile(f);
    setError(null);
    setResult(null);
  }

  function onDrop(e) {
    e.preventDefault();
    setDragging(false);
    handleFile(e.dataTransfer.files[0]);
  }

  async function handleUpload() {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const data = await uploadDataset(file);
      setResult(data);
    } catch (err) {
      setError(err?.response?.data?.detail || 'Erreur lors de l\'upload');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ maxWidth: 680, margin: '0 auto' }}>
      {/* Header */}
      <div className="fade-up" style={{ marginBottom: 32 }}>
        <h1 style={{ fontSize: 28, fontWeight: 800, letterSpacing: '-0.5px', marginBottom: 6 }}>
          Upload Dataset
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Chargez votre fichier CSV ou Excel pour commencer l'analyse
        </p>
      </div>

      {/* Drop zone */}
      <div
        className={`drop-zone fade-up fade-up-1 ${dragging ? 'dragging' : ''}`}
        onClick={() => !result && fileRef.current.click()}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        style={{ cursor: result ? 'default' : 'pointer' }}
      >
        <input
          ref={fileRef}
          type="file"
          accept=".csv,.xlsx,.xls"
          style={{ display: 'none' }}
          onChange={e => handleFile(e.target.files[0])}
        />

        {file ? (
          <div style={{ position: 'relative', zIndex: 1 }}>
            <div style={{
              width: 64, height: 64,
              borderRadius: 14,
              background: 'var(--accent-dim)',
              border: '1px solid rgba(61,127,255,0.3)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              margin: '0 auto 16px',
              boxShadow: '0 0 30px var(--accent-glow)',
            }}>
              <FileText size={28} color="var(--accent)" />
            </div>
            <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 4 }}>{file.name}</div>
            <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
              {(file.size / 1024).toFixed(1)} KB
            </div>
            {!result && (
              <div
                style={{ marginTop: 12, fontSize: 13, color: 'var(--text-muted)', cursor: 'pointer' }}
                onClick={e => { e.stopPropagation(); setFile(null); }}
              >
                Changer de fichier
              </div>
            )}
          </div>
        ) : (
          <div style={{ position: 'relative', zIndex: 1 }}>
            <div className="drop-zone-icon">
              <Upload size={28} color="var(--accent)" />
            </div>
            <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 8 }}>
              Glissez votre fichier ici
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 14, marginBottom: 16 }}>
              ou cliquez pour parcourir
            </div>
            <div style={{ display: 'inline-flex', gap: 8 }}>
              {['CSV', 'XLSX', 'XLS'].map(f => (
                <span key={f} className="chip">{f}</span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Error */}
      {error && (
        <div className="alert alert-error fade-up" style={{ marginTop: 16 }}>
          <AlertCircle size={16} style={{ flexShrink: 0, marginTop: 1 }} />
          {error}
        </div>
      )}

      {/* Upload button */}
      {file && !result && (
        <button
          className="btn btn-primary btn-lg fade-up"
          style={{ width: '100%', marginTop: 16 }}
          onClick={handleUpload}
          disabled={loading}
        >
          {loading ? <><div className="spinner" /> Chargement...</> : <><Upload size={16} /> Uploader le dataset</>}
        </button>
      )}

      {/* Result cards */}
      {result && (
        <div className="fade-up" style={{ marginTop: 24 }}>
          <div className="alert alert-success" style={{ marginBottom: 20 }}>
            <CheckCircle size={16} style={{ flexShrink: 0 }} />
            Dataset chargé avec succès · Run ID : <strong style={{ fontFamily: 'monospace', marginLeft: 6 }}>{result.run_id}</strong>
          </div>

          <div className="grid-3" style={{ marginBottom: 20 }}>
            <div className="stat-card">
              <div className="stat-icon" style={{ background: 'var(--accent-dim)', border: '1px solid rgba(61,127,255,0.2)' }}>
                <Table size={16} color="var(--accent)" />
              </div>
              <div className="stat-value" style={{ color: 'var(--accent)' }}>{result.rows?.toLocaleString()}</div>
              <div className="stat-label">Lignes</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon" style={{ background: 'var(--teal-dim)', border: '1px solid rgba(0,212,170,0.2)' }}>
                <Layers size={16} color="var(--teal)" />
              </div>
              <div className="stat-value" style={{ color: 'var(--teal)' }}>{result.columns}</div>
              <div className="stat-label">Colonnes</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon" style={{ background: 'var(--purple-dim)', border: '1px solid rgba(168,85,247,0.2)' }}>
                <Hash size={16} color="var(--purple)" />
              </div>
              <div className="stat-value" style={{ color: 'var(--purple)' }}>{result.column_names?.length}</div>
              <div className="stat-label">Features</div>
            </div>
          </div>

          {/* Column list */}
          <div className="card" style={{ marginBottom: 20 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '0.06em', fontFamily: 'var(--font-display)' }}>
              Colonnes détectées
            </div>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {result.column_names?.map(col => (
                <span key={col} className="chip">
                  {col}
                  <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>
                    {result.column_types?.[col]?.replace('object', 'str').replace('int64', 'int').replace('float64', 'float')}
                  </span>
                </span>
              ))}
            </div>
          </div>

          <button
            className="btn btn-primary btn-lg"
            style={{ width: '100%' }}
            onClick={() => navigate(`/automl/eda/${result.run_id}`)}
          >
            Continuer vers l'EDA <span style={{ marginLeft: 4 }}>→</span>
          </button>
        </div>
      )}
    </div>
  );
}
