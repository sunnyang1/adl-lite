import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useConfidenceColor } from '@/hooks/useConfidenceColor';

// Test wrapper component
const TestComponent = ({ confidence }: { confidence: number }) => {
  const { level, hexColor, muiColor } = useConfidenceColor(confidence);
  
  return (
    <div>
      <div data-testid="confidence-level">{level}</div>
      <div data-testid="confidence-hex">{hexColor}</div>
      <div data-testid="confidence-mui">{muiColor}</div>
    </div>
  );
};

describe('useConfidenceColor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns high level for confidence >= 0.8', () => {
    render(<TestComponent confidence={0.8} />);
    
    expect(screen.getByTestId('confidence-level')).toHaveTextContent('high');
    expect(screen.getByTestId('confidence-hex')).toHaveTextContent('#4caf50');
    expect(screen.getByTestId('confidence-mui')).toHaveTextContent('success');
  });

  it('returns high level for confidence > 0.8', () => {
    render(<TestComponent confidence={0.95} />);
    
    expect(screen.getByTestId('confidence-level')).toHaveTextContent('high');
    expect(screen.getByTestId('confidence-mui')).toHaveTextContent('success');
  });

  it('returns medium level for confidence >= 0.5 and < 0.8', () => {
    render(<TestComponent confidence={0.5} />);
    
    expect(screen.getByTestId('confidence-level')).toHaveTextContent('medium');
    expect(screen.getByTestId('confidence-hex')).toHaveTextContent('#ff9800');
    expect(screen.getByTestId('confidence-mui')).toHaveTextContent('warning');
  });

  it('returns medium level for confidence between 0.5 and 0.8', () => {
    render(<TestComponent confidence={0.65} />);
    
    expect(screen.getByTestId('confidence-level')).toHaveTextContent('medium');
    expect(screen.getByTestId('confidence-mui')).toHaveTextContent('warning');
  });

  it('returns low level for confidence < 0.5', () => {
    render(<TestComponent confidence={0.4} />);
    
    expect(screen.getByTestId('confidence-level')).toHaveTextContent('low');
    expect(screen.getByTestId('confidence-hex')).toHaveTextContent('#f44336');
    expect(screen.getByTestId('confidence-mui')).toHaveTextContent('error');
  });

  it('returns low level for confidence = 0', () => {
    render(<TestComponent confidence={0} />);
    
    expect(screen.getByTestId('confidence-level')).toHaveTextContent('low');
    expect(screen.getByTestId('confidence-mui')).toHaveTextContent('error');
  });

  it('handles decimal confidence values correctly', () => {
    render(<TestComponent confidence={0.799} />);
    
    // 0.799 < 0.8, should be medium
    expect(screen.getByTestId('confidence-level')).toHaveTextContent('medium');
  });
});
