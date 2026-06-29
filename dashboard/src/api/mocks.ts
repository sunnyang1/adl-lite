import { AdlStatus, SystemMode, EventDict } from '@/api/types';

/** Generate a mock event for a given capability */
function generateMockEvent(
  adlId: string,
  conceptId: string,
  eventType: string,
  actor: string,
  index: number,
  previousEventId: string,
): EventDict {
  const timestamp = new Date(Date.now() - index * 3600_000).toISOString();
  const eventId = `evt-${adlId}-${index}`;
  return {
    event_id: eventId,
    concept_id: conceptId,
    event_type: eventType,
    actor: actor,
    reasoning: `Mock reasoning for ${eventType} event #${index} on ${adlId}`,
    timestamp: timestamp,
    payload: { note: `Event payload ${index}` },
    previous_event_id: previousEventId,
    hash: `hash-${eventId}`,
  };
}

/** Generate mock history events for a capability */
function generateMockHistory(
  adlId: string,
  conceptId: string,
  _status: AdlStatus,
  validators: string[],
  eventCount: number,
): EventDict[] {
  const events: EventDict[] = [];
  let previousId = 'genesis';

  // First event: registration
  events.push(
    generateMockEvent(adlId, conceptId, 'register', validators[0] ?? 'validator-1', 0, previousId),
  );
  previousId = events[0].event_id;

  // Validation events from validators
  const validatorEvents = Math.min(validators.length, eventCount - 1);
  for (let i = 1; i <= validatorEvents; i++) {
    const evt = generateMockEvent(
      adlId,
      conceptId,
      'validate',
      validators[i - 1] ?? `validator-${i}`,
      i,
      previousId,
    );
    events.push(evt);
    previousId = evt.event_id;
  }

  // Fill remaining with miscellaneous events
  for (let i = validatorEvents + 1; i < eventCount; i++) {
    const eventType = i % 3 === 0 ? 'validate' : 'update';
    const evt = generateMockEvent(
      adlId,
      conceptId,
      eventType,
      `actor-${i}`,
      i,
      previousId,
    );
    events.push(evt);
    previousId = evt.event_id;
  }

  return events;
}

/** Mock capabilities with various statuses */
export const MOCK_CAPABILITIES: string[] = [
  'cap-nlp-parser',
  'cap-speech-recognition',
  'cap-image-classifier',
  'cap-sentiment-analyzer',
  'cap-data-ingestion',
];

/** Mock status data per capability */
export const MOCK_STATUSES: Record<string, { status: AdlStatus; confidence: number; validators: string[]; dev_mode: boolean }> = {
  'cap-nlp-parser': { status: 'validated', confidence: 0.92, validators: ['val-alpha', 'val-beta', 'val-gamma'], dev_mode: false },
  'cap-speech-recognition': { status: 'provisional', confidence: 0.65, validators: ['val-alpha', 'val-delta'], dev_mode: false },
  'cap-image-classifier': { status: 'validated', confidence: 0.88, validators: ['val-beta', 'val-epsilon', 'val-gamma'], dev_mode: false },
  'cap-sentiment-analyzer': { status: 'deprecated', confidence: 0.35, validators: ['val-alpha'], dev_mode: true },
  'cap-data-ingestion': { status: 'forked', confidence: 0.72, validators: ['val-delta', 'val-epsilon'], dev_mode: false },
};

/** Mock history events per capability */
export const MOCK_HISTORY: Record<string, EventDict[]> = {
  'cap-nlp-parser': generateMockHistory('cap-nlp-parser', 'nlp-parser', 'validated', ['val-alpha', 'val-beta', 'val-gamma'], 15),
  'cap-speech-recognition': generateMockHistory('cap-speech-recognition', 'speech-recognition', 'provisional', ['val-alpha', 'val-delta'], 10),
  'cap-image-classifier': generateMockHistory('cap-image-classifier', 'image-classifier', 'validated', ['val-beta', 'val-epsilon', 'val-gamma'], 12),
  'cap-sentiment-analyzer': generateMockHistory('cap-sentiment-analyzer', 'sentiment-analyzer', 'deprecated', ['val-alpha'], 18),
  'cap-data-ingestion': generateMockHistory('cap-data-ingestion', 'data-ingestion', 'forked', ['val-delta', 'val-epsilon'], 16),
};

/** Mock system mode */
export const MOCK_MODE: { mode: SystemMode; n_min: number; dev_mode: boolean } = {
  mode: 'moderate',
  n_min: 3,
  dev_mode: false,
};

/** Mock verification results */
export const MOCK_VERIFY: Record<string, { adl_id: string; integrity_ok: boolean }> = {
  'cap-nlp-parser': { adl_id: 'cap-nlp-parser', integrity_ok: true },
  'cap-speech-recognition': { adl_id: 'cap-speech-recognition', integrity_ok: true },
  'cap-image-classifier': { adl_id: 'cap-image-classifier', integrity_ok: true },
  'cap-sentiment-analyzer': { adl_id: 'cap-sentiment-analyzer', integrity_ok: false },
  'cap-data-ingestion': { adl_id: 'cap-data-ingestion', integrity_ok: true },
};
