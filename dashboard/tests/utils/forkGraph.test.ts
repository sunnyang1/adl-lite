import { describe, it, expect } from 'vitest';
import { buildForkGraph, toD3TreeFormat } from '@/utils/forkGraph';
import { EventDict, ForkTreeNode } from '@/api/types';

describe('buildForkGraph', () => {
  it('returns root node with no children for events without fork events', () => {
    const events: EventDict[] = [
      {
        event_id: 'evt-1',
        concept_id: 'concept-1',
        event_type: 'validate',
        actor: 'val-alpha',
        reasoning: 'Validated',
        timestamp: '2024-01-01T00:00:00Z',
        payload: {},
        previous_event_id: 'genesis',
        hash: 'hash-1',
      },
    ];

    const result: ForkTreeNode = buildForkGraph('cap-1', events);
    expect(result.adl_id).toBe('cap-1');
    expect(result.event_type).toBe('root');
    expect(result.children).toEqual([]);
  });

  it('creates child nodes for fork events', () => {
    const events: EventDict[] = [
      {
        event_id: 'evt-1',
        concept_id: 'concept-1',
        event_type: 'fork',
        actor: 'val-alpha',
        reasoning: 'Forked',
        timestamp: '2024-01-01T00:00:00Z',
        payload: { forked_adl_id: 'cap-1-fork-1' },
        previous_event_id: 'genesis',
        hash: 'hash-1',
      },
    ];

    const result: ForkTreeNode = buildForkGraph('cap-1', events);
    expect(result.adl_id).toBe('cap-1');
    expect(result.children.length).toBe(1);
    expect(result.children[0].adl_id).toBe('cap-1-fork-1');
    expect(result.children[0].event_type).toBe('fork');
  });

  it('handles multiple fork events', () => {
    const events: EventDict[] = [
      {
        event_id: 'evt-1',
        concept_id: 'concept-1',
        event_type: 'fork',
        actor: 'val-alpha',
        reasoning: 'Fork 1',
        timestamp: '2024-01-01T00:00:00Z',
        payload: { forked_adl_id: 'cap-1-fork-1' },
        previous_event_id: 'genesis',
        hash: 'hash-1',
      },
      {
        event_id: 'evt-2',
        concept_id: 'concept-1',
        event_type: 'fork',
        actor: 'val-beta',
        reasoning: 'Fork 2',
        timestamp: '2024-01-02T00:00:00Z',
        payload: { forked_adl_id: 'cap-1-fork-2' },
        previous_event_id: 'evt-1',
        hash: 'hash-2',
      },
    ];

    const result: ForkTreeNode = buildForkGraph('cap-1', events);
    expect(result.children.length).toBe(2);
    expect(result.children[0].adl_id).toBe('cap-1-fork-1');
    expect(result.children[1].adl_id).toBe('cap-1-fork-2');
  });

  it('skips fork events without forked_adl_id in payload', () => {
    const events: EventDict[] = [
      {
        event_id: 'evt-1',
        concept_id: 'concept-1',
        event_type: 'fork',
        actor: 'val-alpha',
        reasoning: 'Fork without ID',
        timestamp: '2024-01-01T00:00:00Z',
        payload: {},
        previous_event_id: 'genesis',
        hash: 'hash-1',
      },
    ];

    const result: ForkTreeNode = buildForkGraph('cap-1', events);
    expect(result.children.length).toBe(0);
  });

  it('handles empty events array', () => {
    const result: ForkTreeNode = buildForkGraph('cap-1', []);
    expect(result.adl_id).toBe('cap-1');
    expect(result.children).toEqual([]);
  });
});

describe('toD3TreeFormat', () => {
  it('converts a simple ForkTreeNode to d3-tree format', () => {
    const node: ForkTreeNode = {
      adl_id: 'cap-1',
      event_type: 'root',
      children: [
        { adl_id: 'cap-1-fork-1', event_type: 'fork', children: [] },
      ],
    };

    const result = toD3TreeFormat(node);
    expect(result.name).toBe('cap-1');
    expect(result.children.length).toBe(1);
    expect(result.children[0].name).toBe('cap-1-fork-1');
  });

  it('handles node without children', () => {
    const node: ForkTreeNode = {
      adl_id: 'cap-1',
      event_type: 'root',
      children: [],
    };

    const result = toD3TreeFormat(node);
    expect(result.name).toBe('cap-1');
    expect(result.children).toEqual([]);
  });
});
