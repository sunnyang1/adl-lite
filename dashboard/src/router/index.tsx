import React, { Suspense } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LoadingFallback } from '@/components/shared/LoadingFallback';

// Lazy load page components for code splitting
const OverviewPage = React.lazy(() => import('@/pages/OverviewPage'));
const CapabilitiesPage = React.lazy(() => import('@/pages/CapabilitiesPage'));
const CapabilityDetailPageRoute = React.lazy(() => import('@/pages/CapabilityDetailPageRoute'));
const AgentsPage = React.lazy(() => import('@/pages/AgentsPage'));
const AgentDetailPageRoute = React.lazy(() => import('@/pages/AgentDetailPageRoute'));
const TasksPage = React.lazy(() => import('@/pages/TasksPage'));
const RuntimePage = React.lazy(() => import('@/pages/RuntimePage'));
const TrustPage = React.lazy(() => import('@/pages/TrustPage'));

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
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/agents/:did" element={<AgentDetailPageRoute />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/runtime" element={<RuntimePage />} />
        <Route path="/trust" element={<TrustPage />} />
      </Routes>
    </Suspense>
  );
}
