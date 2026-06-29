import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useEwmaCurve } from '@/hooks/useEwmaCurve';

// Test wrapper component
const TestComponent = ({ events, alpha }: { events: any[]; alpha?: number }) => {
  const ewmaPoints = useEwmaCurve(events, alpha);
  
  return (
    <div>
      <div data-testid="ewma-points-count">{ewmaPoints.length}</div>
      {ewmaPoints.map((point: any, index: number) => (
        <div key={index} data-testid={`ewma-point-${index}`}>
          {point.timestamp}: raw={point.raw}, smoothed={point.smoothed.toFixed(3)}
        </div>
      ))}
    </div>
  );
};

describe('useEwmaCurve', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns empty array when events is empty', () => {
    render(<TestComponent events={[]} />);
    
    expect(screen.getByTestId('ewma-points-count')).toHaveTextContent('0');
  });

  it('computes EWMA curve from events with confidence values', () => {
    const events: any[] = [
      {
        timestamp: '2025-01-01T00:00:00Z',
        payload: { confidence: 0.5 },
      },
      {
        timestamp: '2025-01-02T00:00:00Z',
        payload: { confidence: 0.7 },
      },
      {
        timestamp: '2025-01-03T00:00:00Z',
        payload: { confidence: 0.6 },
      },
    ];

    render(<TestComponent events={events} />);
    
    expect(screen.getByTestId('ewma-points-count')).toHaveTextContent('3');
    // First point: smoothed = raw = 0.5
    expect(screen.getByTestId('ewma-point-0')).toHaveTextContent('raw=0.5');
  });

  it('uses default alpha of 0.3 when not specified', () => {
    const events: any[] = [
      {
        timestamp: '2025-01-01T00:00:00Z',
        payload: { confidence: 0.5 },
      },
      {
        timestamp: '2025-01-02T00:00:00Z',
        payload: { confidence: 0.8 },
      },
    ];

    render(<TestComponent events={events} />);
    
    // With alpha=0.3:
    // s[0] = 0.5
    // s[1] = 0.3 * 0.8 + 0.7 * 0.5 = 0.24 + 0.35 = 0.59
    expect(screen.getByTestId('ewma-point-1')).toHaveTextContent('smoothed=0.590');
  });

  it('uses custom alpha when specified', () => {
    const events: any[] = [
      {
        timestamp: '2025-01-01T00:00:00Z',
        payload: { confidence: 0.5 },
      },
      {
        timestamp: '2025-01-02T00:00:00Z',
        payload: { confidence: 0.8 },
      },
    ];

    render(<TestComponent events={events} alpha={0.5} />);
    
    // With alpha=0.5:
    // s[0] = 0.5
    // s[1] = 0.5 * 0.8 + 0.5 * 0.5 = 0.4 + 0.25 = 0.65
    expect(screen.getByTestId('ewma-point-1')).toHaveTextContent('smoothed=0.650');
  });

  it('handles events with missing confidence values', () => {
    const events: any[] = [
      {
        timestamp: '2025-01-01T00:00:00Z',
        payload: { confidence: 0.5 },
      },
      {
        timestamp: '2025-01-02T00:00:00Z',
        payload: {}, // no confidence
      },
    ];

    render(<TestComponent events={events} />);
    
    // Second event has no confidence, should default to 0
    expect(screen.getByTestId('ewma-points-count')).toHaveTextContent('2');
    expect(screen.getByTestId('ewma-point-1')).toHaveTextContent('raw=0');
  });
});
