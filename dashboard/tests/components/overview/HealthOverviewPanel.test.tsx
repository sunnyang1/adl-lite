import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { HealthOverviewPanel } from '@/components/overview/HealthOverviewPanel';

// Mock the API endpoints
vi.mock('@/api/endpoints', () => ({
  useCapabilities: vi.fn(),
  useMode: vi.fn(),
}));

import { useCapabilities, useMode } from '@/api/endpoints';

describe('HealthOverviewPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders system health overview title', () => {
    (useCapabilities as any).mockReturnValue({
      data: { total: 10, capabilities: ['cap-1', 'cap-2'] },
    });
    (useMode as any).mockReturnValue({
      data: { mode: 'moderate', dev_mode: false },
    });

    render(<HealthOverviewPanel />);
    
    expect(screen.getByText(/system health overview/i)).toBeInTheDocument();
  });

  it('renders total capabilities stat', () => {
    (useCapabilities as any).mockReturnValue({
      data: { total: 10, capabilities: ['cap-1', 'cap-2'] },
    });
    (useMode as any).mockReturnValue({
      data: { mode: 'moderate', dev_mode: false },
    });

    render(<HealthOverviewPanel />);
    
    expect(screen.getByText(/total capabilities/i)).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('renders active capabilities stat', () => {
    (useCapabilities as any).mockReturnValue({
      data: { total: 10, capabilities: ['cap-1', 'cap-2', 'cap-3'] },
    });
    (useMode as any).mockReturnValue({
      data: { mode: 'moderate', dev_mode: false },
    });

    render(<HealthOverviewPanel />);
    
    expect(screen.getByText(/active/i)).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
  });

  it('renders mode indicator', () => {
    (useCapabilities as any).mockReturnValue({
      data: { total: 10, capabilities: ['cap-1'] },
    });
    (useMode as any).mockReturnValue({
      data: { mode: 'dev', dev_mode: true },
    });

    render(<HealthOverviewPanel />);
    
    expect(screen.getByText(/mode/i)).toBeInTheDocument();
  });

  it('handles empty data gracefully', () => {
    (useCapabilities as any).mockReturnValue({
      data: null,
    });
    (useMode as any).mockReturnValue({
      data: null,
    });

    render(<HealthOverviewPanel />);
    
    expect(screen.getByText(/system health overview/i)).toBeInTheDocument();
    // Should show 0 for total and active
    const zeros = screen.getAllByText('0');
    expect(zeros.length).toBeGreaterThan(0);
  });
});
