import Chip from '@mui/material/Chip';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';

interface IntegrityBadgeProps {
  integrityOk: boolean;
}

export function IntegrityBadge({ integrityOk }: IntegrityBadgeProps): JSX.Element {
  if (integrityOk) {
    return (
      <Chip
        icon={<CheckCircleIcon />}
        label="Integrity OK"
        size="small"
        color="success"
        variant="outlined"
      />
    );
  }

  return (
    <Chip
      icon={<ErrorIcon />}
      label="Integrity Failed"
      size="small"
      color="error"
      variant="outlined"
    />
  );
}
