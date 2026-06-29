import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { TransitionDialog } from '@/components/shared/TransitionDialog';

// Mock fetch API
const originalFetch = global.fetch;
beforeEach(() => {
  global.fetch = vi.fn();
});

afterEach(() => {
  global.fetch = originalFetch;
  vi.clearAllMocks();
});

describe('TransitionDialog', () => {
  const mockOnClose = vi.fn();
  const mockOnSuccess = vi.fn();
  const defaultAdlId = 'test-capability';

  beforeEach(() => {
    mockOnClose.mockClear();
    mockOnSuccess.mockClear();
  });

  it('does not render when open is false', () => {
    render(
      <TransitionDialog
        open={false}
        adlId={defaultAdlId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders when open is true', () => {
    render(
      <TransitionDialog
        open={true}
        adlId={defaultAdlId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/transition status/i)).toBeInTheDocument();
  });

  it('displays the adl_id in the dialog', () => {
    render(
      <TransitionDialog
        open={true}
        adlId={defaultAdlId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    expect(screen.getByText(new RegExp(defaultAdlId, 'i'))).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', () => {
    render(
      <TransitionDialog
        open={true}
        adlId={defaultAdlId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    const cancelButton = screen.getByText(/cancel/i);
    fireEvent.click(cancelButton);
    
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('shows validation error when submitting without status', async () => {
    render(
      <TransitionDialog
        open={true}
        adlId={defaultAdlId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    const submitButton = screen.getByTestId('transition-submit-button');
    fireEvent.click(submitButton);
    
    expect(screen.getByText(/please select a status/i)).toBeInTheDocument();
  });

  it('submits transition when form is filled', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        adl_id: defaultAdlId,
        status: 'validated',
        confidence: 0.7,
        validators: ['test-validator'],
        dev_mode: false,
      }),
    });
    
    render(
      <TransitionDialog
        open={true}
        adlId={defaultAdlId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    // Select status - use fireEvent.change for native select
    const statusSelect = screen.getByLabelText(/new status/i);
    fireEvent.change(statusSelect, { target: { value: 'validated' } });
    
    // Fill reason
    const reasonInput = screen.getByLabelText(/reason/i);
    fireEvent.change(reasonInput, { target: { value: 'Testing transition' } });
    
    const submitButton = screen.getByTestId('transition-submit-button');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/consensus/transition',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('validated'),
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
      json: async () => ({ error: 'Transition failed', detail: 'Invalid status transition' }),
    });
    
    render(
      <TransitionDialog
        open={true}
        adlId={defaultAdlId}
        onClose={mockOnClose}
        onSuccess={mockOnSuccess}
      />
    );
    
    // Select status
    const statusSelect = screen.getByLabelText(/new status/i);
    fireEvent.change(statusSelect, { target: { value: 'validated' } });
    
    const submitButton = screen.getByTestId('transition-submit-button');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/invalid status transition/i)).toBeInTheDocument();
    });
    
    expect(mockOnSuccess).not.toHaveBeenCalled();
    expect(mockOnClose).not.toHaveBeenCalled();
  });
});
