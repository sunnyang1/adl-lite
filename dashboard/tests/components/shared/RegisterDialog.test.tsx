import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { RegisterDialog } from '@/components/shared/RegisterDialog';

// Mock fetch API
const originalFetch = global.fetch;
beforeEach(() => {
  global.fetch = vi.fn();
});

afterEach(() => {
  global.fetch = originalFetch;
  vi.clearAllMocks();
});

describe('RegisterDialog', () => {
  const mockOnClose = vi.fn();
  const mockOnSuccess = vi.fn();

  beforeEach(() => {
    mockOnClose.mockClear();
    mockOnSuccess.mockClear();
  });

  it('does not render when open is false', () => {
    render(
      <RegisterDialog open={false} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );
    
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders when open is true', () => {
    render(
      <RegisterDialog open={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );
    
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText(/register new capability/i)).toBeInTheDocument();
  });

  it('calls onClose when cancel button is clicked', () => {
    render(
      <RegisterDialog open={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );
    
    const cancelButton = screen.getByText(/cancel/i);
    fireEvent.click(cancelButton);
    
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('shows validation error when submitting without adl_id', async () => {
    render(
      <RegisterDialog open={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );
    
    const submitButton = screen.getByTestId('register-submit-button');
    fireEvent.click(submitButton);
    
    expect(screen.getByText(/adl id is required/i)).toBeInTheDocument();
  });

  it('submits registration when form is filled', async () => {
    (global.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        adl_id: 'test-capability',
        status: 'provisional',
        confidence: 0.5,
        validators: [],
        dev_mode: false,
      }),
    });
    
    render(
      <RegisterDialog open={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );
    
    const adlIdInput = screen.getByLabelText(/adl id/i);
    fireEvent.change(adlIdInput, { target: { value: 'test-capability' } });
    
    const submitButton = screen.getByTestId('register-submit-button');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        '/api/v1/consensus/register',
        expect.objectContaining({
          method: 'POST',
          body: expect.stringContaining('test-capability'),
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
      json: async () => ({ error: 'Already registered', detail: 'test-capability already exists' }),
    });
    
    render(
      <RegisterDialog open={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );
    
    const adlIdInput = screen.getByLabelText(/adl id/i);
    fireEvent.change(adlIdInput, { target: { value: 'test-capability' } });
    
    const submitButton = screen.getByTestId('register-submit-button');
    fireEvent.click(submitButton);
    
    await waitFor(() => {
      expect(screen.getByText(/already exists/i)).toBeInTheDocument();
    });
    
    expect(mockOnSuccess).not.toHaveBeenCalled();
    expect(mockOnClose).not.toHaveBeenCalled();
  });

  it('clears form when dialog is reopened', () => {
    const { unmount } = render(
      <RegisterDialog open={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );
    
    const adlIdInput = screen.getByLabelText(/adl id/i) as HTMLInputElement;
    fireEvent.change(adlIdInput, { target: { value: 'test-123' } });
    
    expect(adlIdInput.value).toBe('test-123');
    
    unmount();
    
    render(
      <RegisterDialog open={true} onClose={mockOnClose} onSuccess={mockOnSuccess} />
    );
    
    const newAdlIdInput = screen.getByLabelText(/adl id/i) as HTMLInputElement;
    expect(newAdlIdInput.value).toBe('');
  });
});
