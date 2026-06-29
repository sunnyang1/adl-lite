import TableRow from '@mui/material/TableRow';
import TableCell from '@mui/material/TableCell';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { useNavigate } from 'react-router-dom';
import { CapabilitySummary } from '@/api/types';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { ConfidenceDot } from '@/components/shared/ConfidenceDot';
import { formatConfidence } from '@/utils/formatters';

interface CapabilityRowProps {
  summary: CapabilitySummary;
}

export function CapabilityRow({ summary }: CapabilityRowProps): JSX.Element {
  const navigate = useNavigate();

  const handleClick = (): void => {
    navigate(`/capabilities/${summary.adl_id}`);
  };

  return (
    <TableRow
      hover
      onClick={handleClick}
      sx={{ cursor: 'pointer' }}
    >
      <TableCell>
        <Typography variant="body2" fontWeight="500">
          {summary.adl_id}
        </Typography>
      </TableCell>
      <TableCell>
        <StatusBadge status={summary.status} />
      </TableCell>
      <TableCell>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <ConfidenceDot confidence={summary.confidence} />
          <Typography variant="body2">
            {formatConfidence(summary.confidence)}
          </Typography>
        </Box>
      </TableCell>
      <TableCell>
        <Typography variant="body2">{summary.validator_count}</Typography>
      </TableCell>
    </TableRow>
  );
}
