import React, { Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LoadingFallback } from '@/components/shared/LoadingFallback';

// Lazy load page components for code splitting
const OverviewPage = React.lazy(() => import('@/pages/OverviewPage'));
const CapabilitiesPage = React.lazy(() => import('@/pages/CapabilitiesPage'));
const CapabilityDetailPageRoute = React.lazy(() => import('@/pages/CapabilityDetailPageRoute'));

export function AppRouter(): JSX.Element {
  return (
    <Suspense fallback={<LoadingFallback />}>
      <Routes>
        <Route path="/" element={<Navigate to="/overview" replace />} />
        <Route path="/overview" element={<OverviewPage />} />
        <Route path="/capabilities" element={<CapabilitiesPage />} />
        <Route
          path="/capabilities/:adl_id"
          element={<CapabilityDetailPageRoute />}
        />
      </Routes>
    </Suspense>
  );
}
