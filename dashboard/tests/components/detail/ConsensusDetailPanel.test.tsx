import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConsensusDetailPanel } from '@/components/detail/ConsensusDetailPanel';

// Mock the API endpoints
vi.mock('@/api/endpoints', () => ({
  useHistory: vi.fn(),
}));

// Mock the Zustand store
vi.mock('@/store/useModeStore', () => ({
  useModeStore: vi.fn(),
}));

// Mock the useValidatorDetail hook
vi.mock('@/hooks/useValidatorDetail', () => ({
  useValidatorDetail: vi.fn(),
}));

// Mock sub-components
vi.mock('@/components/overview/ConfidenceGauge', () => ({
  ConfidenceGauge: ({ confidence }: any) => (
    <div data-testid="confidence-gauge">Gauge: {confidence}</div>
  ),
}));

vi.mock('@/components/detail/ValidatorVoteRow', () => ({
  ValidatorVoteRow: ({ vote }: any) => (
    <div data-testid={`vote-row-${vote.event_id}`}>
      {vote.validator}: {vote.timestamp}
    </div>
  ),
}));

import { useHistory } from '@/api/endpoints';
import { useModeStore } from '@/store/useModeStore';
import { useValidatorDetail } from '@/hooks/useValidatorDetail';

describe('ConsensusDetailPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    
    // Default mock implementations
    (useHistory as any).mockReturnValue({
      data: { events: [] },
    });
    
    (useModeStore as any).mockImplementation((selector: any) => {
      const state = { nMin: 3 };
      return selector ? selector(state) : state;
    });
    
    (useValidatorDetail as any).mockReturnValue([]);
  });

  it('renders consensus status title', () => {
    render(
      <ConsensusDetailPanel
        validators={['v1', 'v2']}
        confidence={0.75}
        adlId="cap-123"
      />
    );
    
    expect(screen.getByText(/consensus status/i)).toBeInTheDocument();
  });

  it('displays validator count and nMin', () => {
    (useModeStore as any).mockImplementation((selector: any) => {
      const state = { nMin: 3 };
      return selector ? selector(state) : state;
    });

    render(
      <ConsensusDetailPanel
        validators={['v1', 'v2']}
        confidence={0.75}
        adlId="cap-123"
      />
    );
    
    expect(screen.getByText(/validators/i)).toBeInTheDocument();
    expect(screen.getByText(/2\/3/)).toBeInTheDocument();
  });

  it('displays confidence value', () => {
    render(
      <ConsensusDetailPanel
        validators={['v1']}
        confidence={0.85}
        adlId="cap-123"
      />
    );
    
    expect(screen.getByText(/confidence/i)).toBeInTheDocument();
  });

  it('renders confidence gauge', () => {
    render(
      <ConsensusDetailPanel
        validators={['v1']}
        confidence={0.85}
        adlId="cap-123"
      />
    );
    
    expect(screen.getByTestId('confidence-gauge')).toBeInTheDocument();
  });

  it('renders validator votes when available', () => {
    (useValidatorDetail as any).mockReturnValue([
      {
        validator: 'v1',
        event_id: 'e1',
        timestamp: '2025-01-01',
        reasoning: 'Good',
      },
      {
        validator: 'v2',
        event_id: 'e2',
        timestamp: '2025-01-02',
        reasoning: 'Looks good',
      },
    ]);

    render(
      <ConsensusDetailPanel
        validators={['v1', 'v2']}
        confidence={0.85}
        adlId="cap-123"
      />
    );
    
    expect(screen.getByText(/validator votes/i)).toBeInTheDocument();
    expect(screen.getByTestId('vote-row-e1')).toBeInTheDocument();
    expect(screen.getByTestId('vote-row-e2')).toBeInTheDocument();
  });

  it('handles empty validators', () => {
    render(
      <ConsensusDetailPanel
        validators={[]}
        confidence={0}
        adlId="cap-123"
      />
    );
    
    expect(screen.getByText(/0\//)).toBeInTheDocument();
  });
});
