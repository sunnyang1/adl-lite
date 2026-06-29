import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';

describe('ConfirmDialog Accessibility', () => {
  const mockOnConfirm = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    mockOnConfirm.mockClear();
    mockOnCancel.mockClear();
  });

  it('should have proper ARIA attributes', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Delete Confirmation"
        description="Are you sure?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const dialog = screen.getByRole('alertdialog');
    expect(dialog).toBeInTheDocument();
    expect(dialog).toHaveAttribute('aria-modal', 'true');
  });

  it('should have aria-label on dialog', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Delete Confirmation"
        description="Are you sure?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const dialog = screen.getByRole('alertdialog');
    expect(dialog).toHaveAttribute('aria-label', expect.stringContaining('Delete Confirmation'));
  });

  it('should close on Escape key', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Test"
        description="Test"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const dialog = screen.getByRole('alertdialog');
    fireEvent.keyDown(dialog, { key: 'Escape' });

    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('should have accessible buttons', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Test"
        description="Test"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );

    const confirmButton = screen.getByRole('button', { name: /confirm/i });
    const cancelButton = screen.getByRole('button', { name: /cancel/i });

    expect(confirmButton).toBeInTheDocument();
    expect(cancelButton).toBeInTheDocument();
  });
});
