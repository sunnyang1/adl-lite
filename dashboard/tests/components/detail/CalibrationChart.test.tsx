import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CalibrationChart } from '@/components/detail/CalibrationChart';
import type { EwmaPoint } from '@/api/types';

describe('CalibrationChart', () => {
  const mockEwmaPoints: EwmaPoint[] = [
    { timestamp: '2024-01-01T00:00:00Z', raw: 0.5, smoothed: 0.5 },
    { timestamp: '2024-01-02T00:00:00Z', raw: 0.6, smoothed: 0.53 },
    { timestamp: '2024-01-03T00:00:00Z', raw: 0.7, smoothed: 0.571 },
  ];

  it('renders without crashing', () => {
    render(<CalibrationChart ewmaPoints={mockEwmaPoints} />);
    expect(screen.getByTestId('calibration-chart')).toBeInTheDocument();
  });

  it('displays the chart title', () => {
    render(<CalibrationChart ewmaPoints={mockEwmaPoints} />);
    expect(screen.getByText('EWMA Calibration Curve')).toBeInTheDocument();
  });

  it('renders line chart with correct data points', () => {
    render(<CalibrationChart ewmaPoints={mockEwmaPoints} />);

    // Should have line chart elements
    const chartContainer = screen.getByTestId('calibration-chart');
    expect(chartContainer).toBeInTheDocument();

    // Check that the chart has SVG elements (Recharts renders as SVG)
    const svgElement = chartContainer.querySelector('svg');
    expect(svgElement).toBeInTheDocument();
  });

  it('renders both raw and smoothed lines', () => {
    render(<CalibrationChart ewmaPoints={mockEwmaPoints} />);

    // Should have two lines (raw and smoothed)
    const chartContainer = screen.getByTestId('calibration-chart');
    const lineElements = chartContainer.querySelectorAll('.recharts-line');
    expect(lineElements.length).toBeGreaterThanOrEqual(2);
  });

  it('handles empty data gracefully', () => {
    render(<CalibrationChart ewmaPoints={[]} />);

    expect(screen.getByTestId('calibration-chart')).toBeInTheDocument();
    expect(screen.getByText('No calibration data available')).toBeInTheDocument();
  });

  it('applies custom height prop', () => {
    const customHeight = 400;
    render(<CalibrationChart ewmaPoints={mockEwmaPoints} height={customHeight} />);

    const chartContainer = screen.getByTestId('calibration-chart');
    expect(chartContainer).toHaveStyle({ height: `${customHeight}px` });
  });
});
