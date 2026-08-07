import { describe, it, expect } from 'vitest';
import { availableTaskActions, FALLBACK_TASK_ACTIONS } from '@/utils/taskActions';
import { TaskStatus } from '@/api/types';

const META_TRANSITIONS = {
  open: ['assigned', 'in_progress', 'closed'],
  assigned: ['in_progress'],
  in_progress: ['in_progress', 'submitted'],
  submitted: ['validated', 'rejected'],
  rejected: ['in_progress', 'closed'],
  validated: ['closed'],
  closed: [],
};

describe('availableTaskActions (meta-driven)', () => {
  it('maps backend transitions to frontend action kinds', () => {
    expect(availableTaskActions('open', META_TRANSITIONS)).toEqual([
      'claim',
      'close',
    ]);
    expect(availableTaskActions('assigned', META_TRANSITIONS)).toEqual([
      'claim',
    ]);
    expect(availableTaskActions('in_progress', META_TRANSITIONS)).toEqual([
      'claim',
      'submit',
    ]);
    expect(availableTaskActions('submitted', META_TRANSITIONS)).toEqual([
      'validate',
    ]);
    expect(availableTaskActions('validated', META_TRANSITIONS)).toEqual([
      'close',
    ]);
    expect(availableTaskActions('rejected', META_TRANSITIONS)).toEqual([
      'claim',
      'close',
    ]);
  });

  it('treats an empty target list as authoritative (terminal state)', () => {
    expect(availableTaskActions('closed', META_TRANSITIONS)).toEqual([]);
  });

  it('deduplicates targets that map to the same action', () => {
    const transitions = { open: ['assigned', 'in_progress'] };
    expect(availableTaskActions('open', transitions)).toEqual(['claim']);
  });
});

describe('availableTaskActions (fallback)', () => {
  it('falls back to the hardcoded mapping when transitions are missing', () => {
    const statuses: TaskStatus[] = [
      'open',
      'assigned',
      'in_progress',
      'submitted',
      'validated',
      'rejected',
      'closed',
    ];
    for (const status of statuses) {
      expect(availableTaskActions(status, null)).toEqual(
        FALLBACK_TASK_ACTIONS[status],
      );
      expect(availableTaskActions(status, undefined)).toEqual(
        FALLBACK_TASK_ACTIONS[status],
      );
      expect(availableTaskActions(status, {})).toEqual(
        FALLBACK_TASK_ACTIONS[status],
      );
    }
  });

  it('falls back when the status is missing from the meta map', () => {
    expect(availableTaskActions('open', { assigned: ['in_progress'] })).toEqual(
      FALLBACK_TASK_ACTIONS.open,
    );
  });

  it('ignores transition targets that have no action mapping', () => {
    const transitions = { open: ['closed', 'unknown_state'] };
    expect(availableTaskActions('open', transitions)).toEqual(['close']);
  });
});
