import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Breadcrumbs from '@mui/material/Breadcrumbs';
import Link from '@mui/material/Link';
import { useParams, useNavigate } from 'react-router-dom';
import { useStatus, useHistory, useVerify } from '@/api/endpoints';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { ConfidenceDot } from '@/components/shared/ConfidenceDot';
import { IntegrityBadge } from '@/components/detail/IntegrityBadge';
import { ChainTimelineView } from '@/components/detail/ChainTimelineView';
import { ConsensusDetailPanel } from '@/components/detail/ConsensusDetailPanel';
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton';
import { ErrorAlert } from '@/components/shared/ErrorAlert';
import { formatConfidence } from '@/utils/formatters';

export function CapabilityDetailPage(): JSX.Element {
  const { adl_id } = useParams<{ adl_id: string }>();
  const navigate = useNavigate();

  const {
    data: statusData,
    isLoading: statusLoading,
    error: statusError,
    refetch: refetchStatus,
  } = useStatus(adl_id ?? '');

  const {
    data: historyData,
    isLoading: historyLoading,
  } = useHistory(adl_id ?? '');

  const { data: verifyData } = useVerify(adl_id ?? '');

  if (statusLoading || historyLoading) {
    return <LoadingSkeleton count={4} />;
  }

  if (statusError) {
    return (
      <ErrorAlert
        message={`Failed to load capability: ${adl_id}`}
        onRetry={refetchStatus}
      />
    );
  }

  const status = statusData;
  const events = historyData?.events ?? [];
  const integrityOk = verifyData?.integrity_ok ?? true;

  if (!status) {
    return (
      <ErrorAlert
        message="Capability not found"
        onRetry={refetchStatus}
      />
    );
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Breadcrumbs sx={{ mb: 1 }}>
        <Link
          underline="hover"
          color="inherit"
          onClick={() => navigate('/capabilities')}
          sx={{ cursor: 'pointer' }}
        >
          Capabilities
        </Link>
        <Typography color="text.primary">{adl_id}</Typography>
      </Breadcrumbs>

      {/* Header */}
      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Typography variant="h4" fontWeight="bold">
            {adl_id}
          </Typography>
          <StatusBadge status={status.status} />
          <ConfidenceDot confidence={status.confidence} />
          <Typography variant="body1">
            γ = {formatConfidence(status.confidence)}
          </Typography>
          <IntegrityBadge integrityOk={integrityOk} />
        </Box>
      </Paper>

      {/* Timeline */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Event Chain Timeline
        </Typography>
        <ChainTimelineView events={events} />
      </Paper>

      {/* Consensus */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Consensus Detail
        </Typography>
        <ConsensusDetailPanel
          validators={status.validators}
          confidence={status.confidence}
          adlId={adl_id ?? ''}
        />
      </Paper>
    </Box>
  );
}
