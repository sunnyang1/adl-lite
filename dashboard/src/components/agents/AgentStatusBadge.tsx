import Chip from '@mui/material/Chip';
import { AgentStatus } from '@/api/types';

interface AgentStatusBadgeProps {
  status: AgentStatus;
}

const STATUS_LABELS: Record<AgentStatus, string> = {
  pending: 'Pending',
  active: 'Active',
  deprecated: 'Deprecated',
};

const STATUS_EMOJIS: Record<AgentStatus, string> = {
  pending: '⏳',
  active: '🟢',
  deprecated: '🔴',
};

const STATUS_MUI_COLORS: Record<AgentStatus, 'default' | 'success' | 'error'> = {
  pending: 'default',
  active: 'success',
  deprecated: 'error',
};

export function AgentStatusBadge({ status }: AgentStatusBadgeProps): JSX.Element {
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
