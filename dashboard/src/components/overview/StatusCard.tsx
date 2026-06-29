import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';

interface StatusCardProps {
  label: string;
  value: string;
  icon: string;
  color?: string;
}

export function StatusCard({
  label,
  value,
  icon,
  color = 'text.primary',
}: StatusCardProps): JSX.Element {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        display: 'flex',
        flexDirection: 'column',
        gap: 1,
        height: '100%',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="h4" sx={{ fontSize: '1.5rem' }}>
          {icon}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {label}
        </Typography>
      </Box>
      <Typography variant="h3" sx={{ color, fontWeight: 700 }}>
        {value}
      </Typography>
    </Paper>
  );
}
