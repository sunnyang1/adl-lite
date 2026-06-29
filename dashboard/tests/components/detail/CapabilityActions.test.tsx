import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CapabilityActions } from '@/components/detail/CapabilityActions';

// Mock the dialog components
vi.mock('@/components/shared/ModeToggleDialog', () => ({
  ModeToggleDialog: ({ open, onClose }: any) =>
    open ? (
      <div data-testid="mode-toggle-dialog">
        Mode Toggle Dialog
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

vi.mock('@/components/shared/RegisterDialog', () => ({
  RegisterDialog: ({ open, onClose }: any) =>
    open ? (
      <div data-testid="register-dialog">
        Register Dialog
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

vi.mock('@/components/shared/TransitionDialog', () => ({
  TransitionDialog: ({ open, onClose }: any) =>
    open ? (
      <div data-testid="transition-dialog">
        Transition Dialog
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

vi.mock('@/components/shared/ForkDialog', () => ({
  ForkDialog: ({ open, originalId, onClose }: any) =>
    open ? (
      <div data-testid="fork-dialog">
        Fork Dialog
        <span>Original Capability: {originalId}</span>
        <button onClick={onClose}>Close</button>
      </div>
    ) : null,
}));

describe('CapabilityActions', () => {
  const mockAdlId = 'test-capability-123';
  const mockStatus = 'provisional';

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all action buttons', () => {
    render(<CapabilityActions adlId={mockAdlId} status={mockStatus} />);
    
    expect(screen.getByText(/toggle mode/i)).toBeInTheDocument();
    expect(screen.getByText(/register/i)).toBeInTheDocument();
    expect(screen.getByText(/transition/i)).toBeInTheDocument();
    expect(screen.getByText(/fork/i)).toBeInTheDocument();
  });

  it('opens mode toggle dialog when toggle mode button is clicked', () => {
    render(<CapabilityActions adlId={mockAdlId} status={mockStatus} />);
    
    const toggleButton = screen.getByText(/toggle mode/i);
    fireEvent.click(toggleButton);
    
    expect(screen.getByTestId('mode-toggle-dialog')).toBeInTheDocument();
  });

  it('opens register dialog when register button is clicked', () => {
    render(<CapabilityActions adlId={mockAdlId} status={mockStatus} />);
    
    const registerButton = screen.getByText(/register/i);
    fireEvent.click(registerButton);
    
    expect(screen.getByTestId('register-dialog')).toBeInTheDocument();
  });

  it('opens transition dialog when transition button is clicked', () => {
    render(<CapabilityActions adlId={mockAdlId} status={mockStatus} />);
    
    const transitionButton = screen.getByText(/transition/i);
    fireEvent.click(transitionButton);
    
    expect(screen.getByTestId('transition-dialog')).toBeInTheDocument();
  });

  it('opens fork dialog when fork button is clicked', () => {
    render(<CapabilityActions adlId={mockAdlId} status={mockStatus} />);
    
    const forkButton = screen.getByText(/fork/i);
    fireEvent.click(forkButton);
    
    expect(screen.getByTestId('fork-dialog')).toBeInTheDocument();
  });

  it('passes adlId to fork dialog', () => {
    render(<CapabilityActions adlId={mockAdlId} status={mockStatus} />);
    
    const forkButton = screen.getByText(/fork/i);
    fireEvent.click(forkButton);
    
    expect(screen.getByText(/original capability/i)).toBeInTheDocument();
  });

  it('closes dialogs when onClose is called', () => {
    render(<CapabilityActions adlId={mockAdlId} status={mockStatus} />);
    
    // Open mode toggle dialog
    const toggleButton = screen.getByText(/toggle mode/i);
    fireEvent.click(toggleButton);
    expect(screen.getByTestId('mode-toggle-dialog')).toBeInTheDocument();
    
    // Close it
    const closeButton = screen.getByText('Close');
    fireEvent.click(closeButton);
    expect(screen.queryByTestId('mode-toggle-dialog')).not.toBeInTheDocument();
  });
});
