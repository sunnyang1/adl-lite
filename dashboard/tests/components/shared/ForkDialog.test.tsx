import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ForkDialog } from '@/components/shared/ForkDialog';

// Mock fetch API
const originalFetch = global.fetch;
beforeEach(() => {
  global.fetch = vi.fn();
});

afterEach(() => {
  global.fetch = originalFetch;
  vi.clearAllMocks();
});

describe('ForkDialog', () => {
  const mockOnClose = vi.fn();
  const mockOnSuccess = vi.fn();
  const defaultOriginalId = 'test-capability';

  beforeEach(() => {
    mockOnClose.mockClear();
    mockOnSuccess.mockClear();
  });

  it('does not render when open is false', () => {
    render(
      <ForkDialog
        open={false}
        originalId={defaultOriginalId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders when open is true', () => {
    render(
      <ForkDialog
        open={true}
        originalId={defaultOriginalId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/original capability/i)).toBeInTheDocument();
  });

  it('displays the original capability id in the dialog', () => {
    render(
      <ForkDialog
        open={true}
        originalId={defaultOriginalId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    expect(screen.getByText(new RegExp(defaultOriginalId, 'i'))).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', () => {
    render(
      <ForkDialog
        open={true}
        originalId={defaultOriginalId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    const cancelButton = screen.getByText(/cancel/i);
    fireEvent.click(cancelButton);
    
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('shows validation error when submitting without fork_id', async () => {
    render(
      <ForkDialog
        open={true}
        originalId={defaultOriginalId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    const submitButton = screen.getByTestId('fork-submit-button');
    fireEvent.click(submitButton);
    
    expect(screen.getByText(/fork id is required/i)).toBeInTheDocument();
  });

  it('submits fork when form is filled', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        adl_id: 'forked-capability',
        status: 'provisional',
        confidence: 0.5,
        validators: [],
        dev_mode: false,
      }),
    });
    
    render(
      <ForkDialog
        open={true}
        originalId={defaultOriginalId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    // Fill fork ID
    const forkIdInput = screen.getByLabelText(/fork id/i);
    fireEvent.change(forkIdInput, { target: { value: 'forked-capability' } });
    
    // Fill reason
    const reasonInput = screen.getByLabelText(/reason/i);
    fireEvent.change(reasonInput, { target: { value: 'Testing fork' } });
    
    const submitButton = screen.getByTestId('fork-submit-button');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/consensus/fork',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('forked-capability'),
        })
      );
    });
    
    expect(mockOnSuccess).toHaveBeenCalledTimes(1);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('handles API error gracefully', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: false,
      status: 409,
      json: async () => ({ error: 'Fork failed', detail: 'Original capability not found' }),
    });
    
    render(
      <ForkDialog
        open={true}
        originalId={defaultOriginalId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    // Fill fork ID
    const forkIdInput = screen.getByLabelText(/fork id/i);
    fireEvent.change(forkIdInput, { target: { value: 'forked-capability' } });
    
    const submitButton = screen.getByTestId('fork-submit-button');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/not found/i)).toBeInTheDocument();
    });
    
    expect(mockOnSuccess).not.toHaveBeenCalled();
    expect(mockOnClose).not.toHaveBeenCalled();
  });

  it('clears form when dialog is reopened', () => {
    const { unmount } = render(
      <ForkDialog
        open={true}
        originalId={defaultOriginalId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    const forkIdInput = screen.getByLabelText(/fork id/i) as HTMLInputElement;
    fireEvent.change(forkIdInput, { target: { value: 'test-123' } });
    
    expect(forkIdInput.value).toBe('test-123');
    
    unmount();
    
    render(
      <ForkDialog
        open={true}
        originalId={defaultOriginalId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    const newForkIdInput = screen.getByLabelText(/fork id/i) as HTMLInputElement;
    expect(newForkIdInput.value).toBe('');
  });
});
