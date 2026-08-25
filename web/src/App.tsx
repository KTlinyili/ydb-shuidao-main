import { Navigate, Route, Routes } from 'react-router-dom';
import MainLayout from '@/layouts/MainLayout';
import DashboardPage from '@/pages/DashboardPage';
import LiveMonitorPage from '@/pages/LiveMonitorPage';
import PestIdentifyPage from '@/pages/PestIdentifyPage';
import EnvMonitorPage from '@/pages/EnvMonitorPage';
import RiskWarningPage from '@/pages/RiskWarningPage';
import ConsultPage from '@/pages/ConsultPage';
import FieldMapPage from '@/pages/FieldMapPage';
import KnowledgePage from '@/pages/KnowledgePage';
import DevicePage from '@/pages/DevicePage';
import HistoryPage from '@/pages/HistoryPage';
import SettingsPage from '@/pages/SettingsPage';

export default function App() {
  return (
    <Routes>
      <Route element={<MainLayout />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/live" element={<LiveMonitorPage />} />
        <Route path="/identify" element={<PestIdentifyPage />} />
        <Route path="/environment" element={<EnvMonitorPage />} />
        <Route path="/warnings" element={<RiskWarningPage />} />
        <Route path="/consult" element={<ConsultPage />} />
        <Route path="/map" element={<FieldMapPage />} />
        <Route path="/knowledge" element={<KnowledgePage />} />
        <Route path="/devices" element={<DevicePage />} />
        <Route path="/history" element={<HistoryPage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Route>
    </Routes>
  );
}
