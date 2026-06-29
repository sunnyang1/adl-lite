import Chip from '@mui/material/Chip';
import { AdlStatus } from '@/api/types';
import { STATUS_EMOJI_MAP } from '@/utils/constants';

interface StatusBadgeProps {
  status: AdlStatus;
}

const STATUS_LABELS: Record<AdlStatus, string> = {
  provisional: 'Provisional',
  validated: 'Validated',
  deprecated: 'Deprecated',
  forked: 'Forked',
  archived: 'Archived',
};

const STATUS_MUI_COLORS: Record<AdlStatus, 'warning' | 'success' | 'error' | 'info' | 'default'> = {
  provisional: 'warning',
  validated: 'success',
  deprecated: 'error',
  forked: 'info',
  archived: 'default',
};

export function StatusBadge({ status }: StatusBadgeProps): JSX.Element {
  const emoji: string = STATUS_EMOJI_MAP[status] ?? '⚪';
  const label: string = STATUS_LABELS[status] ?? status;
  const color: 'warning' | 'success' | 'error' | 'info' | 'default' =
    STATUS_MUI_COLORS[status] ?? 'default';

  return (
    <Chip
      label={`${emoji} ${label}`}
      size="small"
      color={color}
      variant="outlined"
      className="status-badge"
    />
  );
}
