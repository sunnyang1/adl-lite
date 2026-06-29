import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ModeToggleDialog } from '@/components/shared/ModeToggleDialog';
import { useModeStore } from '@/store/useModeStore';

// Mock fetch API
const originalFetch = global.fetch;
beforeEach(() => {
  global.fetch = vi.fn();
});

afterEach(() => {
  global.fetch = originalFetch;
  vi.clearAllMocks();
  useModeStore.getState().setMode('moderate', 3, false);
});

describe('ModeToggleDialog', () => {
  const mockOnClose = vi.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
  });

  it('does not render when open is false', () => {
    render(
      <ModeToggleDialog open={false} onClose={mockOnClose} />
    );
    
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders when open is true', () => {
    render(
      <ModeToggleDialog open={true} onClose={mockOnClose} />
    );
    
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/toggle system mode/i)).toBeInTheDocument();
  });

  it('displays current mode from store', () => {
    useModeStore.getState().setMode('lenient', 1, true);
    
    render(
      <ModeToggleDialog open={true} onClose={mockOnClose} />
    );
    
    expect(screen.getByText(/dev/i)).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', () => {
    render(
      <ModeToggleDialog open={true} onClose={mockOnClose} />
    );
    
    const cancelButton = screen.getByText(/cancel/i);
    fireEvent.click(cancelButton);
    
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('switches to dev mode when dev button is clicked', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ mode: 'dev', n_min: 1, dev_mode: true }),
    });
    
    render(
      <ModeToggleDialog open={true} onClose={mockOnClose} />
    );
    
    const devButton = screen.getByText(/switch to dev/i);
    fireEvent.click(devButton);
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/consensus/mode/dev',
        expect.objectContaining({ method: 'POST' })
      );
    });
    
    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
    
    const state = useModeStore.getState();
    expect(state.devMode).toBe(true);
    expect(state.currentMode).toBe('dev');
  });

  it('switches to production mode when production button is clicked', async () => {
    useModeStore.getState().setMode('strict', 1, true);
    
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ mode: 'production', n_min: 3, dev_mode: false }),
    });
    
    render(
      <ModeToggleDialog open={true} onClose={mockOnClose} />
    );
    
    const productionButton = screen.getByText(/switch to production/i);
    fireEvent.click(productionButton);
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/consensus/mode/production',
        expect.objectContaining({ method: 'POST' })
      );
    });
    
    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
    
    const state = useModeStore.getState();
    expect(state.devMode).toBe(false);
    expect(state.currentMode).toBe('production');
  });

  it('handles API error gracefully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 500,
    });
    
    render(
      <ModeToggleDialog open={true} onClose={mockOnClose} />
    );
    
    const devButton = screen.getByText(/switch to dev/i);
    fireEvent.click(devButton);
    
    // Should show error message
    await waitFor(() => {
      expect(screen.getByText(/failed to switch/i)).toBeInTheDocument();
    });
    
    // Should not close dialog on error
    expect(mockOnClose).not.toHaveBeenCalled();
  });
});
