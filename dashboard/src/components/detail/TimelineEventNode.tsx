import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import { EventDict } from '@/api/types';
import { formatTimestamp, truncateId } from '@/utils/formatters';

interface TimelineEventNodeProps {
  event: EventDict;
}

const EVENT_TYPE_LABELS: Record<string, string> = {
  register: 'Register',
  validate: 'Validate',
  update: 'Update',
  fork: 'Fork',
  deprecate: 'Deprecate',
};

export function TimelineEventNode({
  event,
}: TimelineEventNodeProps): JSX.Element {
  const typeLabel: string =
    EVENT_TYPE_LABELS[event.event_type] ?? event.event_type;

  return (
    <Box sx={{ py: 0.5 }} className="timeline-event-node">
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
        <Chip
          label={typeLabel}
          size="small"
          variant="outlined"
          sx={{ fontWeight: 600 }}
        />
        <Typography variant="caption" color="text.secondary">
          {formatTimestamp(event.timestamp)}
        </Typography>
      </Box>
      <Typography variant="body2">
        <strong>Actor:</strong> {event.actor}
      </Typography>
      {event.reasoning && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
          {event.reasoning}
        </Typography>
      )}
      <Typography variant="caption" color="text.secondary" sx={{ mt: 0.25 }}>
        Hash: {truncateId(event.hash, 16)}
      </Typography>
    </Box>
  );
}
