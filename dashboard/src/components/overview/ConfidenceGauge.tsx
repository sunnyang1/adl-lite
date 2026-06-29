import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { getConfidenceColorHex } from '@/utils/confidenceColor';
import { formatConfidence } from '@/utils/formatters';

interface ConfidenceGaugeProps {
  confidence: number;
  size?: number;
}

export function ConfidenceGauge({
  confidence,
  size = 120,
}: ConfidenceGaugeProps): JSX.Element {
  const color: string = getConfidenceColorHex(confidence);
  const percentage: number = Math.round(confidence * 100);

  // SVG circular gauge
  const strokeWidth: number = 8;
  const radius: number = (size - strokeWidth) / 2;
  const circumference: number = 2 * Math.PI * radius;
  const offset: number = circumference - (percentage / 100) * circumference;

  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        gap: 1,
      }}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="#e0e0e0"
          strokeWidth={strokeWidth}
        />
        {/* Confidence arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        {/* Center text */}
        <text
          x={size / 2}
          y={size / 2}
          textAnchor="middle"
          dominantBaseline="central"
          fill={color}
          fontSize={size / 5}
          fontWeight="bold"
        >
          {formatConfidence(confidence, 0)}
        </text>
      </svg>
      <Typography variant="caption" color="text.secondary">
        Confidence (γ)
      </Typography>
    </Box>
  );
}
