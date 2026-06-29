import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';

describe('ConfirmDialog', () => {
  const mockOnConfirm = vi.fn();
  const mockOnCancel = vi.fn();

  beforeEach(() => {
    mockOnConfirm.mockClear();
    mockOnCancel.mockClear();
  });

  it('does not render when open is false', () => {
    render(
      <ConfirmDialog
        open={false}
        title="Test Title"
        description="Test Description"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('renders when open is true', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Test Title"
        description="Test Description"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });

  it('displays the title', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Delete Confirmation"
        description="Test Description"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    expect(screen.getByText('Delete Confirmation')).toBeInTheDocument();
  });

  it('displays the description', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Test Title"
        description="Are you sure you want to delete this item?"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    expect(screen.getByText('Are you sure you want to delete this item?')).toBeInTheDocument();
  });

  it('calls onConfirm when confirm button is clicked', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Test Title"
        description="Test Description"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    const confirmButton = screen.getByText(/confirm/i);
    fireEvent.click(confirmButton);
    
    expect(mockOnConfirm).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when cancel button is clicked', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Test Title"
        description="Test Description"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    const cancelButton = screen.getByText(/cancel/i);
    fireEvent.click(cancelButton);
    
    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('calls onCancel when dialog is closed via backdrop click', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Test Title"
        description="Test Description"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
      />
    );
    
    // MUI Dialog fires onClose when backdrop is clicked
    const dialog = screen.getByRole('dialog');
    fireEvent.keyDown(dialog, { key: 'Escape' });
    
    expect(mockOnCancel).toHaveBeenCalledTimes(1);
  });

  it('renders with custom confirm button text', () => {
    render(
      <ConfirmDialog
        open={true}
        title="Test Title"
        description="Test Description"
        onConfirm={mockOnConfirm}
        onCancel={mockOnCancel}
        confirmText="Delete"
        cancelText="Keep"
      />
    );
    
    expect(screen.getByText('Delete')).toBeInTheDocument();
    expect(screen.getByText('Keep')).toBeInTheDocument();
  });
});
