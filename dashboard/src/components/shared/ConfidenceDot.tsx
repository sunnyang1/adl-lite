import Box from '@mui/material/Box';
import { getConfidenceColorHex } from '@/utils/confidenceColor';

interface ConfidenceDotProps {
  confidence: number;
}

export function ConfidenceDot({ confidence }: ConfidenceDotProps): JSX.Element {
  const color: string = getConfidenceColorHex(confidence);

  return (
    <Box
      className="confidence-dot"
      sx={{
        display: 'inline-block',
        width: 12,
        height: 12,
        borderRadius: '50%',
        bgcolor: color,
      }}
    />
  );
}
