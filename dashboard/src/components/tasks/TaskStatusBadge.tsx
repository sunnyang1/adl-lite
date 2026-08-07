import Chip from '@mui/material/Chip';
import { TaskStatus } from '@/api/types';

interface TaskStatusBadgeProps {
  status: TaskStatus;
}

const STATUS_LABELS: Record<TaskStatus, string> = {
  open: 'Open',
  assigned: 'Assigned',
  in_progress: 'In Progress',
  submitted: 'Submitted',
  validated: 'Validated',
  rejected: 'Rejected',
  closed: 'Closed',
};

const STATUS_EMOJIS: Record<TaskStatus, string> = {
  open: '📭',
  assigned: '🔵',
  in_progress: '🟠',
  submitted: '🟣',
  validated: '🟢',
  rejected: '🔴',
  closed: '⚪',
};

const STATUS_MUI_COLORS: Record<
  TaskStatus,
  'default' | 'primary' | 'secondary' | 'error' | 'info' | 'success' | 'warning'
> = {
  open: 'info',
  assigned: 'primary',
  in_progress: 'warning',
  submitted: 'secondary',
  validated: 'success',
  rejected: 'error',
  closed: 'default',
};

export function TaskStatusBadge({ status }: TaskStatusBadgeProps): JSX.Element {
  return (
    <Chip
      label={`${STATUS_EMOJIS[status] ?? '⚪'} ${STATUS_LABELS[status] ?? status}`}
      size="small"
      color={STATUS_MUI_COLORS[status] ?? 'default'}
      variant="outlined"
      className="status-badge"
    />
  );
}
