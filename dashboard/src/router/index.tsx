import { Routes, Route, Navigate } from 'react-router-dom';
import { OverviewPage } from '@/pages/OverviewPage';
import { CapabilitiesPage } from '@/pages/CapabilitiesPage';
import { CapabilityDetailPageRoute } from '@/pages/CapabilityDetailPageRoute';

export function AppRouter(): JSX.Element {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/overview" replace />} />
      <Route path="/overview" element={<OverviewPage />} />
      <Route path="/capabilities" element={<CapabilitiesPage />} />
      <Route
        path="/capabilities/:adl_id"
        element={<CapabilityDetailPageRoute />}
      />
    </Routes>
  );
}
