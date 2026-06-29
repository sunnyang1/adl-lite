import { useMemo } from 'react';
import { EventDict, ValidatorVote } from '@/api/types';

/**
 * Extract per-validator votes from capability history events.
 *
 * Scans events for validation-type entries, mapping each to a
 * ValidatorVote with the validator name, event ID, timestamp, and reasoning.
 *
 * @param events - Array of events from the capability history
 * @returns Array of ValidatorVote objects
 */
export function useValidatorDetail(
  events: EventDict[],
): ValidatorVote[] {
  const votes = useMemo(() => {
    const validatorVotes: ValidatorVote[] = [];

    for (const event of events) {
      if (event.event_type === 'validate') {
        validatorVotes.push({
          validator: event.actor,
          event_id: event.event_id,
          timestamp: event.timestamp,
          reasoning: event.reasoning,
        });
      }
    }

    return validatorVotes;
  }, [events]);

  return votes;
}
