import { TaskStatus } from '@/api/types';
import { TaskActionKind } from '@/components/tasks/TaskActionDialog';

/**
 * Hardcoded fallback legal actions per task status.
 *
 * Mirrors the backend state machine (`_TASK_TRANSITIONS` in
 * adl_lite/agents/task.py). Used when `/api/v1/meta/task-transitions` is
 * unavailable (loading, 404, network error) so the UI never regresses:
 * - open:        → assigned / in_progress (claim), closed (close)
 * - assigned:    → in_progress (claim)
 * - in_progress: → in_progress (idempotent re-claim, M3 recovery), submitted (submit)
 * - submitted:   → validated / rejected (validate)
 * - rejected:    → in_progress (claim rework), closed (close)
 * - validated:   → closed (close)
 * - closed:      terminal
 */
export const FALLBACK_TASK_ACTIONS: Record<TaskStatus, TaskActionKind[]> = {
  open: ['claim', 'close'],
  assigned: ['claim'],
  in_progress: ['claim', 'submit'],
  submitted: ['validate'],
  validated: ['close'],
  rejected: ['claim', 'close'],
  closed: [],
};

/**
 * Maps a backend transition TARGET status to the frontend action that
 * performs that transition:
 * - assigned   → claim   (claim assigns the task)
 * - in_progress → claim  (claim moves open/assigned tasks into progress)
 * - submitted  → submit
 * - validated  → validate (validate accepts)
 * - rejected   → validate (validate rejects — same dialog, accepted=false)
 * - closed     → close
 */
export const TRANSITION_TO_ACTION: Record<TaskStatus, TaskActionKind> = {
  open: 'claim',
  assigned: 'claim',
  in_progress: 'claim',
  submitted: 'submit',
  validated: 'validate',
  rejected: 'validate',
  closed: 'close',
};

/** Type of the raw `transitions` field of `/api/v1/meta/task-transitions`. */
export type TransitionMap = Record<string, TaskStatus[]>;

/**
 * Compute the legal actions for a task status.
 *
 * When a meta transition map is available it becomes the single source of
 * truth: each transition target is mapped to the frontend action kind and
 * duplicates are removed (e.g. `open -> [assigned, in_progress]` both map to
 * `claim`). When the map is missing or lacks the status, fall back to the
 * hardcoded mapping so behavior is preserved.
 *
 * @param status - Current task status.
 * @param transitions - Optional transition map from the meta endpoint.
 * @returns Deduplicated action kinds, or an empty array for terminal states.
 */
export function availableTaskActions(
  status: TaskStatus,
  transitions?: TransitionMap | null,
): TaskActionKind[] {
  const nextStatuses = transitions?.[status];
  if (nextStatuses && Array.isArray(nextStatuses)) {
    // The meta map is authoritative when it defines the status — an empty
    // array (terminal state) intentionally disables all actions.
    const kinds: TaskActionKind[] = [];
    for (const next of nextStatuses) {
      const kind = TRANSITION_TO_ACTION[next];
      if (kind && !kinds.includes(kind)) {
        kinds.push(kind);
      }
    }
    return kinds;
  }
  return FALLBACK_TASK_ACTIONS[status] ?? [];
}
