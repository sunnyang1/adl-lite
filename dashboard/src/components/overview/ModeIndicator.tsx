import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { SystemMode } from '@/api/types';

interface ModeIndicatorProps {
  mode: SystemMode;
  devMode: boolean;
}

const MODE_COLORS: Record<SystemMode, string> = {
  strict: '#f44336',
  moderate: '#ff9800',
  lenient: '#4caf50',
};

const MODE_LABELS: Record<SystemMode, string> = {
  strict: 'Strict',
  moderate: 'Moderate',
  lenient: 'Lenient',
};

export function ModeIndicator({
  mode,
  devMode,
}: ModeIndicatorProps): JSX.Element {
  const modeColor: string = MODE_COLORS[mode];
  const modeLabel: string = MODE_LABELS[mode];

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Chip
        label={modeLabel}
        size="small"
        sx={{
          bgcolor: modeColor,
          color: '#fff',
          fontWeight: 600,
        }}
      />
      {devMode && (
        <Chip
          label="DEV"
          size="small"
          variant="outlined"
          color="warning"
          sx={{ fontWeight: 600 }}
        />
      )}
      <Typography variant="body2" color="text.secondary">
        System Mode
      </Typography>
    </Box>
  );
}
