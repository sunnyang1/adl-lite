import { create } from 'zustand';
import { AdlStatus } from '@/api/types';

interface SelectionState {
  selectedAdlId: string | null;
  searchQuery: string;
  statusFilter: AdlStatus | 'all';
  confidenceRange: [number, number];
  setSelectedAdlId: (adlId: string | null) => void;
  setSearchQuery: (query: string) => void;
  setStatusFilter: (filter: AdlStatus | 'all') => void;
  setConfidenceRange: (range: [number, number]) => void;
  clearFilters: () => void;
}

export const useSelectionStore = create<SelectionState>((set) => ({
  selectedAdlId: null,
  searchQuery: '',
  statusFilter: 'all',
  confidenceRange: [0, 1],
  setSelectedAdlId: (adlId: string | null) => set({ selectedAdlId: adlId }),
  setSearchQuery: (query: string) => set({ searchQuery: query }),
  setStatusFilter: (filter: AdlStatus | 'all') => set({ statusFilter: filter }),
  setConfidenceRange: (range: [number, number]) => set({ confidenceRange: range }),
  clearFilters: () =>
    set({
      searchQuery: '',
      statusFilter: 'all',
      confidenceRange: [0, 1],
    }),
}));
