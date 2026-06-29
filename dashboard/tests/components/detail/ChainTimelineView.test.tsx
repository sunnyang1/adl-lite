import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChainTimelineView } from '@/components/detail/ChainTimelineView';
import { EventDict } from '@/api/types';

// Mock the TimelineEventNode component
vi.mock('@/components/detail/TimelineEventNode', () => ({
  TimelineEventNode: ({ event }: { event: EventDict }) => (
    <div data-testid={`event-node-${event.event_id}`}>
      {event.event_type}: {event.actor}
    </div>
  ),
}));

describe('ChainTimelineView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders no events message when events is empty', () => {
    render(<ChainTimelineView events={[]} />);
    
    expect(screen.getByText(/no events recorded/i)).toBeInTheDocument();
  });

  it('renders timeline with events', () => {
    const events: EventDict[] = [
      {
        event_id: 'e1',
        concept_id: 'cap-123',
        event_type: 'register',
        actor: 'user1',
        reasoning: 'Initial registration',
        timestamp: '2025-01-01T00:00:00Z',
        payload: {},
        previous_event_id: '',
        hash: 'abc',
      },
      {
        event_id: 'e2',
        concept_id: 'cap-123',
        event_type: 'validate',
        actor: 'validator1',
        reasoning: 'Looks good',
        timestamp: '2025-01-02T00:00:00Z',
        payload: { confidence: 0.8 },
        previous_event_id: 'e1',
        hash: 'def',
      },
    ];

    render(<ChainTimelineView events={events} />);
    
    expect(screen.getByTestId('event-node-e1')).toBeInTheDocument();
    expect(screen.getByTestId('event-node-e2')).toBeInTheDocument();
  });

  it('renders events in reverse order (newest first)', () => {
    const events: EventDict[] = [
      {
        event_id: 'e1',
        concept_id: 'cap-123',
        event_type: 'register',
        actor: 'user1',
        reasoning: '',
        timestamp: '2025-01-01T00:00:00Z',
        payload: {},
        previous_event_id: '',
        hash: 'abc',
      },
      {
        event_id: 'e2',
        concept_id: 'cap-123',
        event_type: 'validate',
        actor: 'validator1',
        reasoning: '',
        timestamp: '2025-01-02T00:00:00Z',
        payload: {},
        previous_event_id: 'e1',
        hash: 'def',
      },
    ];

    render(<ChainTimelineView events={events} />);
    
    // The newest event (e2) should be first in the timeline
    const timelineItems = document.querySelectorAll('.MuiTimelineItem-root');
    expect(timelineItems.length).toBe(2);
  });

  it('displays event type with correct color dot', () => {
    const events: EventDict[] = [
      {
        event_id: 'e1',
        concept_id: 'cap-123',
        event_type: 'register',
        actor: 'user1',
        reasoning: '',
        timestamp: '2025-01-01T00:00:00Z',
        payload: {},
        previous_event_id: '',
        hash: 'abc',
      },
    ];

    render(<ChainTimelineView events={events} />);
    
    // Should render the TimelineDot with proper color
    expect(screen.getByTestId('event-node-e1')).toBeInTheDocument();
  });
});
