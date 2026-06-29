import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary } from '@/components/shared/ErrorBoundary';

// Component that throws an error for testing
function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error message');
  }
  return <div>No error</div>;
}

// Component that throws a custom error
function CustomErrorComponent() {
  throw new Error('Custom error details');
}

describe('ErrorBoundary', () => {
  // Suppress console.error for these tests
  const originalError = console.error;
  beforeAll(() => {
    console.error = vi.fn();
  });
  afterAll(() => {
    console.error = originalError;
  });

  beforeEach(() => {
    vi.clearAllMocks();
    // Reset import.meta.env.DEV to original value
    vi.unstubAllEnvs();
  });

  describe('RED Phase - Error Boundary Tests', () => {
    it('should render children when there is no error', () => {
      render(
        <ErrorBoundary>
          <div>Test content</div>
        </ErrorBoundary>
      );

      expect(screen.getByText('Test content')).toBeInTheDocument();
    });

    it('should catch errors and display fallback UI', () => {
      render(
        <ErrorBoundary>
          <ThrowingComponent shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /try again/i })).toBeInTheDocument();
    });

    it('should display error message in development mode', () => {
      vi.stubEnv('DEV', true);

      render(
        <ErrorBoundary>
          <CustomErrorComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText(/custom error details/i)).toBeInTheDocument();
    });

    it('should not display error details in production mode', () => {
      vi.stubEnv('DEV', false);
      vi.stubEnv('MODE', 'production');

      render(
        <ErrorBoundary>
          <CustomErrorComponent />
        </ErrorBoundary>
      );

      expect(screen.queryByText(/custom error details/i)).not.toBeInTheDocument();
      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();
    });

    it('should reset error state when "Try again" is clicked', () => {
      const { rerender } = render(
        <ErrorBoundary>
          <ThrowingComponent shouldThrow={true} />
        </ErrorBoundary>
      );

      expect(screen.getByText(/something went wrong/i)).toBeInTheDocument();

      const tryAgainButton = screen.getByRole('button', { name: /try again/i });
      fireEvent.click(tryAgainButton);

      // After reset, the error boundary should render children again
      // We need to trigger a re-render with non-throwing component
      rerender(
        <ErrorBoundary key="reset">
          <div>No error</div>
        </ErrorBoundary>
      );

      expect(screen.getByText('No error')).toBeInTheDocument();
    });

    it('should log error to console when caught', () => {
      render(
        <ErrorBoundary>
          <CustomErrorComponent />
        </ErrorBoundary>
      );

      expect(console.error).toHaveBeenCalledWith(
        expect.stringContaining('ErrorBoundary caught an error'),
        expect.any(Error),
        expect.any(Object)
      );
    });

    it('should render custom fallback when provided', () => {
      const customFallback = <div>Custom error message</div>;

      render(
        <ErrorBoundary fallback={customFallback}>
          <CustomErrorComponent />
        </ErrorBoundary>
      );

      expect(screen.getByText('Custom error message')).toBeInTheDocument();
      expect(screen.queryByText(/something went wrong/i)).not.toBeInTheDocument();
    });
  });
});
