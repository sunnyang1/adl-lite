import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { useForkTree } from '@/hooks/useForkTree';

// Test wrapper component
const TestComponent = ({ adlId, events }: { adlId: string; events: any[] }) => {
  const { forkTree, d3TreeData } = useForkTree(adlId, events);
  
  return (
    <div>
      <div data-testid="fork-tree-root">{forkTree.adl_id}</div>
      <div data-testid="fork-tree-children-count">{forkTree.children.length}</div>
      <div data-testid="d3-tree-name">{d3TreeData.name}</div>
      <div data-testid="d3-tree-children-count">{d3TreeData.children.length}</div>
    </div>
  );
};

describe('useForkTree', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns fork tree with root adlId when no fork events', () => {
    const adlId = 'cap-123';
    const events: any[] = [
      {
        event_id: 'e1',
        event_type: 'register',
        payload: {},
      },
      {
        event_id: 'e2',
        event_type: 'validate',
        payload: { confidence: 0.8 },
      },
    ];

    render(<TestComponent adlId={adlId} events={events} />);
    
    expect(screen.getByTestId('fork-tree-root')).toHaveTextContent(adlId);
    expect(screen.getByTestId('fork-tree-children-count')).toHaveTextContent('0');
  });

  it('builds fork tree from events with fork events', () => {
    const adlId = 'cap-123';
    const events: any[] = [
      {
        event_id: 'e1',
        event_type: 'fork',
        payload: { forked_adl_id: 'cap-123-fork1' },
      },
      {
        event_id: 'e2',
        event_type: 'fork',
        payload: { forked_adl_id: 'cap-123-fork2' },
      },
    ];

    render(<TestComponent adlId={adlId} events={events} />);
    
    expect(screen.getByTestId('fork-tree-root')).toHaveTextContent(adlId);
    expect(screen.getByTestId('fork-tree-children-count')).toHaveTextContent('2');
  });

  it('returns d3-compatible tree data', () => {
    const adlId = 'cap-123';
    const events: any[] = [
      {
        event_id: 'e1',
        event_type: 'fork',
        payload: { forked_adl_id: 'cap-123-fork1' },
      },
    ];

    render(<TestComponent adlId={adlId} events={events} />);
    
    expect(screen.getByTestId('d3-tree-name')).toHaveTextContent(adlId);
    expect(screen.getByTestId('d3-tree-children-count')).toHaveTextContent('1');
  });

  it('handles empty events array', () => {
    const adlId = 'cap-123';
    const events: any[] = [];

    render(<TestComponent adlId={adlId} events={events} />);
    
    expect(screen.getByTestId('fork-tree-root')).toHaveTextContent(adlId);
    expect(screen.getByTestId('fork-tree-children-count')).toHaveTextContent('0');
  });
});
