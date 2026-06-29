import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ConfidenceRangeFilter } from '@/components/shared/ConfidenceRangeFilter';
import { useSelectionStore } from '@/store/useSelectionStore';

// Mock the store
vi.mock('@/store/useSelectionStore');

describe('ConfidenceRangeFilter', () => {
  const mockSetConfidenceRange = vi.fn();
  const mockClearFilters = vi.fn();

  beforeEach(() => {
    (useSelectionStore as any).mockReturnValue({
      confidenceRange: [0, 1],
      setConfidenceRange: mockSetConfidenceRange,
      clearFilters: mockClearFilters,
    });
    mockSetConfidenceRange.mockClear();
    mockClearFilters.mockClear();
  });

  it('renders without crashing', () => {
    render(<ConfidenceRangeFilter />);
    expect(screen.getByTestId('confidence-range-filter')).toBeInTheDocument();
  });

  it('renders with correct initial values from store', () => {
    (useSelectionStore as any).mockReturnValue({
      confidenceRange: [0.2, 0.8],
      setConfidenceRange: mockSetConfidenceRange,
      clearFilters: mockClearFilters,
    });

    render(<ConfidenceRangeFilter />);
    
    // Check that the component displays the correct range
    const rangeDisplay = screen.getByTestId('range-display');
    expect(rangeDisplay).toHaveTextContent('0.20');
    expect(rangeDisplay).toHaveTextContent('0.80');
  });

  it('calls setConfidenceRange with default values when reset is clicked', () => {
    (useSelectionStore as any).mockReturnValue({
      confidenceRange: [0.2, 0.8],
      setConfidenceRange: mockSetConfidenceRange,
      clearFilters: mockClearFilters,
    });

    render(<ConfidenceRangeFilter />);
    
    const resetButton = screen.getByTestId('reset-button');
    fireEvent.click(resetButton);
    
    expect(mockSetConfidenceRange).toHaveBeenCalledWith([0, 1]);
  });

  it('displays min and max labels', () => {
    render(<ConfidenceRangeFilter />);
    
    expect(screen.getByText(/min/i)).toBeInTheDocument();
    expect(screen.getByText(/max/i)).toBeInTheDocument();
  });

  it('applies custom height prop', () => {
    const customHeight = 100;
    render(<ConfidenceRangeFilter height={customHeight} />);
    
    const filterContainer = screen.getByTestId('confidence-range-filter');
    expect(filterContainer).toHaveStyle({ height: `${customHeight}px` });
  });
});
