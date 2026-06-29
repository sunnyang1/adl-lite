import Timeline from '@mui/lab/Timeline';
import TimelineItem from '@mui/lab/TimelineItem';
import TimelineSeparator from '@mui/lab/TimelineSeparator';
import TimelineConnector from '@mui/lab/TimelineConnector';
import TimelineContent from '@mui/lab/TimelineContent';
import TimelineDot from '@mui/lab/TimelineDot';
import Typography from '@mui/material/Typography';
import { EventDict } from '@/api/types';
import { TimelineEventNode } from '@/components/detail/TimelineEventNode';

interface ChainTimelineViewProps {
  events: EventDict[];
}

const EVENT_TYPE_COLORS: Record<string, string> = {
  register: '#2196f3',
  validate: '#4caf50',
  update: '#ff9800',
  fork: '#9c27b0',
  deprecate: '#f44336',
};

export function ChainTimelineView({
  events,
}: ChainTimelineViewProps): JSX.Element {
  if (events.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No events recorded for this capability.
      </Typography>
    );
  }

  const reversedEvents: EventDict[] = [...events].reverse();

  return (
    <Timeline position="right">
      {reversedEvents.map((event: EventDict, index: number) => {
        const dotColor: string =
          EVENT_TYPE_COLORS[event.event_type] ?? '#757575';
        const isLast: boolean = index === reversedEvents.length - 1;

        return (
          <TimelineItem key={event.event_id}>
            <TimelineSeparator>
              <TimelineDot sx={{ bgcolor: dotColor }} />
              {!isLast && <TimelineConnector />}
            </TimelineSeparator>
            <TimelineContent>
              <TimelineEventNode event={event} />
            </TimelineContent>
          </TimelineItem>
        );
      })}
    </Timeline>
  );
}
