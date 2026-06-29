import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CapabilityExplorer } from '@/components/capabilities/CapabilityExplorer';

// Mock the API endpoints
vi.mock('@/api/endpoints', () => ({
  useCapabilities: vi.fn(),
}));

// Mock the Zustand store
vi.mock('@/store/useSelectionStore', () => ({
  useSelectionStore: vi.fn(),
}));

// Mock sub-components
vi.mock('@/components/capabilities/CapabilitySearchBar', () => ({
  CapabilitySearchBar: () => <div data-testid="search-bar">Search Bar</div>,
}));

vi.mock('@/components/capabilities/CapabilityRow', () => ({
  CapabilityRow: ({ summary }: any) => (
    <tr data-testid={`capability-row-${summary.adl_id}`}>
      <td>{summary.adl_id}</td>
    </tr>
  ),
}));

vi.mock('@/components/shared/ConfidenceRangeFilter', () => ({
  ConfidenceRangeFilter: () => <div data-testid="confidence-range-filter">Confidence Range</div>,
}));

import { useCapabilities } from '@/api/endpoints';
import { useSelectionStore } from '@/store/useSelectionStore';

describe('CapabilityExplorer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default mock implementations
    (useCapabilities as any).mockReturnValue({
      data: {
        capabilities: ['cap-1', 'cap-2', 'cap-3'],
        total: 3,
      },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
    
    (useSelectionStore as any).mockImplementation((selector: any) => {
      // Return default values for the store
      const state = {
        searchQuery: '',
        statusFilter: 'all',
        confidenceRange: [0, 1] as [number, number],
      };
      return selector ? selector(state) : state;
    });
  });

  it('renders capability explorer title', () => {
    render(<CapabilityExplorer />);
    
    expect(screen.getByText(/capability explorer/i)).toBeInTheDocument();
  });

  it('renders capability rows', () => {
    render(<CapabilityExplorer />);
    
    expect(screen.getByTestId('capability-row-cap-1')).toBeInTheDocument();
    expect(screen.getByTestId('capability-row-cap-2')).toBeInTheDocument();
    expect(screen.getByTestId('capability-row-cap-3')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    (useCapabilities as any).mockReturnValue({
      data: null,
      isLoading: true,
      error: null,
      refetch: vi.fn(),
    });

    render(<CapabilityExplorer />);
    
    // Should NOT show the title when loading
    expect(screen.queryByText(/capability explorer/i)).not.toBeInTheDocument();
    // Should show skeleton (check for MUI Skeleton)
    expect(document.querySelector('.MuiSkeleton-root')).toBeInTheDocument();
  });

  it('shows error state', () => {
    (useCapabilities as any).mockReturnValue({
      data: null,
      isLoading: false,
      error: new Error('Failed'),
      refetch: vi.fn(),
    });

    render(<CapabilityExplorer />);
    
    // Should show error alert
    expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
  });

  it('renders search bar', () => {
    render(<CapabilityExplorer />);
    
    expect(screen.getByTestId('search-bar')).toBeInTheDocument();
  });

  it('filters by search query', () => {
    // Mock store to return a search query
    (useSelectionStore as any).mockImplementation((selector: any) => {
      const state = {
        searchQuery: 'cap-1',
        statusFilter: 'all',
        confidenceRange: [0, 1] as [number, number],
      };
      return selector ? selector(state) : state;
    });

    render(<CapabilityExplorer />);
    
    // Should only show cap-1
    expect(screen.getByTestId('capability-row-cap-1')).toBeInTheDocument();
    expect(screen.queryByTestId('capability-row-cap-2')).not.toBeInTheDocument();
  });
});
