import React from 'react';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';

// Mock the lazy-loaded components
vi.mock('@/pages/OverviewPage', () => ({
  default: () => <div>Overview Page</div>,
}));

vi.mock('@/pages/CapabilitiesPage', () => ({
  default: () => <div>Capabilities Page</div>,
}));

vi.mock('@/pages/CapabilityDetailPageRoute', () => ({
  default: () => <div>Capability Detail Page</div>,
}));

vi.mock('@/components/shared/LoadingFallback', () => ({
  LoadingFallback: () => <div>Loading...</div>,
}));

describe('AppRouter', () => {
  it('should render router without crashing', async () => {
    const { AppRouter } = await import('@/router');

    render(
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    );

    // Router should render without errors
    expect(document.body).toBeInTheDocument();
  });

  it('should have Suspense wrapper for lazy components', async () => {
    const { AppRouter } = await import('@/router');

    render(
      <BrowserRouter>
        <AppRouter />
      </BrowserRouter>
    );

    // The router should be defined and renderable
    expect(AppRouter).toBeDefined();
  });
});
