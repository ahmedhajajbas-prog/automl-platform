import axios from 'axios';

const BASE = '/api/migration';

// ─── 1. Upload fichier Java ───────────────────────────────────────────────
// POST /api/migration/upload
// Body : FormData { file: File }
// Returns : { message, filename, size_bytes }
export async function uploadJavaFile(file) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await axios.post(`${BASE}/upload`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

// ─── 2. Lancer la migration ───────────────────────────────────────────────
// POST /api/migration/migrate?filename=X&target_version=17
// Returns : {
//   status, filename, target_version,
//   original_code, migrated_code,
//   summary, modifications,
//   analysis_before, analysis_after,
//   score_before, score_after, improvement,
//   saved_file
// }
export async function migrateFile(filename, targetVersion = '17') {
  const { data } = await axios.post(`${BASE}/migrate`, null, {
    params: { filename, target_version: targetVersion },
  });
  return data;
}

// ─── 3. Télécharger le fichier migré ─────────────────────────────────────
// GET /api/migration/download/{filename}
// Returns : fichier .java (téléchargement direct)
export function getDownloadUrl(filename) {
  const stem = filename.replace('.java', '').replace('_migrated', '');
  return `${BASE}/download/${stem}_migrated.java`;
}

export async function downloadMigratedFile(filename) {
  const url = getDownloadUrl(filename);
  const { data } = await axios.get(url, { responseType: 'blob' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(data);
  link.download = `${filename.replace('.java', '')}_migrated.java`;
  link.click();
  URL.revokeObjectURL(link.href);
}

// ─── 4. Historique des fichiers migrés ───────────────────────────────────
// GET /api/migration/history
// Returns : { count, files: [{ filename, size_bytes, download_url }] }
export async function getMigrationHistory() {
  const { data } = await axios.get(`${BASE}/history`);
  return data;
}