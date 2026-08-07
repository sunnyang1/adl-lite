import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Grid from '@mui/material/Grid';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import { useRuntimeStatus } from '@/api/endpoints';
import { RuntimeAgentState } from '@/api/types';
import { StatusCard } from '@/components/overview/StatusCard';
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton';
import { ErrorAlert } from '@/components/shared/ErrorAlert';
import { errorMessage } from '@/utils/errors';

export function RuntimeOverview(): JSX.Element {
  const { data, isLoading, error, refetch } = useRuntimeStatus();

  if (isLoading) {
    return <LoadingSkeleton count={4} />;
  }

  if (error) {
    return (
      <ErrorAlert
        message={errorMessage(error, 'Failed to load runtime status')}
        onRetry={refetch}
      />
    );
  }

  const pending: number = data?.pending ?? 0;
  const queueDepth: number = data?.queue_depth ?? 0;
  const agents: Record<string, RuntimeAgentState> = data?.agents ?? {};
  const agentEntries: [string, RuntimeAgentState][] = Object.entries(agents);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="h5" gutterBottom>
        Runtime Overview
      </Typography>

      <Grid container spacing={2}>
        <Grid item xs={12} sm={6}>
          <StatusCard
            label="Pending Backlog"
            value={String(pending)}
            icon="📥"
            color="warning.main"
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <StatusCard
            label="Queue Depth"
            value={String(queueDepth)}
            icon="🔀"
            color="primary.main"
          />
        </Grid>
      </Grid>

      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" gutterBottom>
          Agent Runtime States
        </Typography>
        {agentEntries.length === 0 ? (
          <Alert severity="info" data-testid="runtime-empty-state">
            <strong>暂无运行中的 Agent。</strong> run_forever 循环由{' '}
            <code>adl-lite run</code> 单进程启动；启动后这里会显示每个 agent 的
            运行状态与已完成任务数。
          </Alert>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>DID</TableCell>
                  <TableCell>Role</TableCell>
                  <TableCell>Running</TableCell>
                  <TableCell>Tasks Done</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {agentEntries.map(([did, state]) => (
                  <TableRow key={did}>
                    <TableCell>
                      <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>
                        {did}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{state.role}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={state.running ? 'Running' : 'Idle'}
                        size="small"
                        color={state.running ? 'success' : 'default'}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2">{state.tasks_done}</Typography>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Paper>
    </Box>
  );
}
