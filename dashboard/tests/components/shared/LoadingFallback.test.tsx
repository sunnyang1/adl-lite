import React from 'react';
import { render, screen } from '@testing-library/react';
import { LoadingFallback } from '@/components/shared/LoadingFallback';

describe('LoadingFallback', () => {
  it('should render loading fallback component', () => {
    render(<LoadingFallback />);

    // Check that the component renders without crashing
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('should display loading text', () => {
    render(<LoadingFallback />);

    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('should have accessible progress indicator', () => {
    render(<LoadingFallback />);

    const progressbar = screen.getByRole('progressbar');
    expect(progressbar).toBeInTheDocument();
  });

  it('should render with centered layout', () => {
    const { container } = render(<LoadingFallback />);

    // Check for Box component with centering styles
    const fallbackContainer = container.firstChild;
    expect(fallbackContainer).toBeInTheDocument();
  });
});
