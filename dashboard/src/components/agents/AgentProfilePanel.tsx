import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Grid from '@mui/material/Grid';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Divider from '@mui/material/Divider';
import { useAgent, useAgentReputation, useAgentHistory } from '@/api/endpoints';
import { AgentStatusBadge } from '@/components/agents/AgentStatusBadge';
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton';
import { ErrorAlert } from '@/components/shared/ErrorAlert';
import { formatTimestamp } from '@/utils/formatters';
import { errorMessage } from '@/utils/errors';

interface AgentProfilePanelProps {
  did: string;
}

/** Small stat tile used inside the reputation grid */
function ReputationStat({
  label,
  value,
}: {
  label: string;
  value: string;
}): JSX.Element {
  return (
    <Paper variant="outlined" sx={{ p: 1.5, height: '100%' }}>
      <Typography variant="body2" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h6" sx={{ fontWeight: 700, mt: 0.5 }}>
        {value}
      </Typography>
    </Paper>
  );
}

/** Format a 0..1 rate as a percentage string */
function formatRate(rate: number | undefined | null): string {
  if (rate === undefined || rate === null || Number.isNaN(rate)) {
    return '—';
  }
  return `${(rate * 100).toFixed(1)}%`;
}

export function AgentProfilePanel({ did }: AgentProfilePanelProps): JSX.Element | null {
  const {
    data: agent,
    isLoading: agentLoading,
    error: agentError,
    refetch: refetchAgent,
  } = useAgent(did);

  const {
    data: reputation,
    isLoading: reputationLoading,
    error: reputationError,
    refetch: refetchReputation,
  } = useAgentReputation(did);

  const {
    data: historyData,
    isLoading: historyLoading,
    error: historyError,
    refetch: refetchHistory,
  } = useAgentHistory(did);

  // Guard: the drawer may mount this panel before a target is selected.
  // Without a DID the queries are disabled, so render nothing instead of
  // flashing an "Agent not found" state.
  if (!did) {
    return null;
  }

  if (agentLoading || reputationLoading || historyLoading) {
    return <LoadingSkeleton count={4} />;
  }

  if (agentError || reputationError || historyError) {
    return (
      <ErrorAlert
        message={
          errorMessage(agentError ?? reputationError ?? historyError) ||
          `Failed to load agent: ${did}`
        }
        onRetry={() => {
          refetchAgent();
          refetchReputation();
          refetchHistory();
        }}
      />
    );
  }

  if (!agent) {
    return <ErrorAlert message={`Agent not found: ${did}`} />;
  }

  const events = historyData?.events ?? [];

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      {/* Profile */}
      <Paper sx={{ p: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flexWrap: 'wrap', mb: 1.5 }}>
          <Typography variant="h6" fontWeight="bold">
            {agent.name}
          </Typography>
          <AgentStatusBadge status={agent.status} />
          <Chip label={agent.role} size="small" variant="outlined" color="secondary" />
        </Box>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
          <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>
            <strong>DID:</strong> {agent.did}
          </Typography>
          <Typography variant="body2">
            <strong>Scope:</strong> {agent.scope || 'public'}
          </Typography>
          <Typography variant="body2">
            <strong>Validator count:</strong> {agent.validator_count}
          </Typography>
        </Box>
      </Paper>

      {/* Reputation */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Reputation
        </Typography>
        <Grid container spacing={1.5}>
          <Grid item xs={6} sm={4}>
            <ReputationStat label="Score v2" value={String(reputation?.score_v2 ?? '—')} />
          </Grid>
          <Grid item xs={6} sm={4}>
            <ReputationStat label="Validated" value={String(reputation?.validate_count ?? 0)} />
          </Grid>
          <Grid item xs={6} sm={4}>
            <ReputationStat label="Submitted" value={String(reputation?.submit_count ?? 0)} />
          </Grid>
          <Grid item xs={6} sm={4}>
            <ReputationStat label="Accepted" value={String(reputation?.accepted_count ?? 0)} />
          </Grid>
          <Grid item xs={6} sm={4}>
            <ReputationStat label="Task success" value={formatRate(reputation?.task_success_rate)} />
          </Grid>
          <Grid item xs={6} sm={4}>
            <ReputationStat label="Fork merge" value={formatRate(reputation?.fork_merge_rate)} />
          </Grid>
          <Grid item xs={6} sm={4}>
            <ReputationStat label="Deprecation" value={formatRate(reputation?.deprecation_rate)} />
          </Grid>
        </Grid>
        {reputation?.note && (
          <Alert severity="info" sx={{ mt: 1.5 }}>
            {reputation.note}
          </Alert>
        )}
      </Paper>

      {/* Event timeline */}
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Event History
        </Typography>
        {events.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            No events recorded yet.
          </Typography>
        ) : (
          <List dense disablePadding>
            {events.map((event, index) => (
              <Box key={event.event_id ?? index}>
                {index > 0 && <Divider component="li" />}
                <ListItem alignItems="flex-start" disableGutters sx={{ px: 0.5 }}>
                  <ListItemText
                    primary={
                      <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                        <Chip label={event.event_type} size="small" variant="outlined" />
                        <Typography variant="caption" color="text.secondary">
                          {event.actor}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {formatTimestamp(event.timestamp)}
                        </Typography>
                      </Box>
                    }
                    secondary={
                      event.reasoning ? (
                        <Typography variant="body2" component="span" sx={{ mt: 0.5, display: 'block' }}>
                          {event.reasoning}
                        </Typography>
                      ) : undefined
                    }
                  />
                </ListItem>
              </Box>
            ))}
          </List>
        )}
      </Paper>
    </Box>
  );
}
