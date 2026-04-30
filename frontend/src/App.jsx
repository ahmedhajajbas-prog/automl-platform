import { Routes, Route, Navigate } from 'react-router-dom';
import Navbar from './components/Navbarbb';
import Home from './pages/Home';
import AutoMLLayout from './pages/automl/AutoMLLayout';
import UploadPage from './pages/automl/UploadPage';
import EdaPage from './pages/automl/EdaPage';
import TrainPage from './pages/automl/TrainPage';
import PredictPage from './pages/automl/PredictPage';
import MigrationHome from './pages/migration/MigrationHome';
import './index.css';

export default function App() {
  return (
    
      <div className="app-shell">
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />

          {/* AutoML — layout avec sidebar */}
          <Route path="/automl" element={<AutoMLLayout />}>
            <Route index element={<Navigate to="/automl/upload" replace />} />
            <Route path="upload" element={<UploadPage />} />
            <Route path="eda/:runId" element={<EdaPage />} />
            <Route path="train/:runId" element={<TrainPage />} />
            <Route path="predict/:runId" element={<PredictPage />} />
          </Route>

          {/* Migration */}
          <Route path="/migration" element={<MigrationHome />} />

          {/* Fallback */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    
  );
}
