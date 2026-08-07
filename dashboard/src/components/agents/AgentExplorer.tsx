import { useState } from 'react';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TablePagination from '@mui/material/TablePagination';
import Snackbar from '@mui/material/Snackbar';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import AddIcon from '@mui/icons-material/Add';
import VisibilityIcon from '@mui/icons-material/Visibility';
import ThumbUpIcon from '@mui/icons-material/ThumbUp';
import BlockIcon from '@mui/icons-material/Block';
import VerifiedUserIcon from '@mui/icons-material/VerifiedUser';
import { useAgents, useAgentDeprecate } from '@/api/endpoints';
import { Agent, AgentStatus } from '@/api/types';
import { useAuthStore, isAdminUser } from '@/store/authStore';
import { AgentStatusBadge } from '@/components/agents/AgentStatusBadge';
import { RegisterAgentDialog } from '@/components/agents/RegisterAgentDialog';
import { ValidateAgentDialog } from '@/components/agents/ValidateAgentDialog';
import { AdminValidateDialog } from '@/components/agents/AdminValidateDialog';
import { RegisterAdminKeyPanel } from '@/components/agents/RegisterAdminKeyPanel';
import { AgentDetailDrawer } from '@/components/agents/AgentDetailDrawer';
import { ConfirmDialog } from '@/components/shared/ConfirmDialog';
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton';
import { ErrorAlert } from '@/components/shared/ErrorAlert';
import { errorMessage } from '@/utils/errors';

/** An agent may no longer be validated or deprecated once deprecated */
function canDeprecate(status: AgentStatus): boolean {
  return status !== 'deprecated';
}

export function AgentExplorer(): JSX.Element {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const [registerOpen, setRegisterOpen] = useState(false);
  const [validateTarget, setValidateTarget] = useState<Agent | null>(null);
  const [adminValidateTarget, setAdminValidateTarget] = useState<Agent | null>(null);
  const [deprecateTarget, setDeprecateTarget] = useState<Agent | null>(null);
  const [detailTarget, setDetailTarget] = useState<Agent | null>(null);
  const [snackbar, setSnackbar] = useState<string | null>(null);

  const user = useAuthStore((state) => state.user);
  const admin: boolean = isAdminUser(user);

  const {
    data,
    isLoading,
    error,
    refetch,
  } = useAgents(page * rowsPerPage, rowsPerPage);

  const deprecateMutation = useAgentDeprecate(deprecateTarget?.did ?? '');

  const agents: Agent[] = data?.agents ?? [];
  const total: number = data?.total ?? 0;

  if (isLoading) {
    return <LoadingSkeleton count={6} />;
  }

  if (error) {
    return <ErrorAlert message="Failed to load agents" onRetry={refetch} />;
  }

  const handleDeprecateConfirm = (): void => {
    if (!deprecateTarget) {
      return;
    }
    deprecateMutation.mutate(
      { actor: 'admin', reason: 'Deprecated from dashboard' },
      {
        onSuccess: () => {
          setSnackbar(`Agent ${deprecateTarget.did} deprecated`);
          setDeprecateTarget(null);
        },
      },
    );
  };

  return (
    <Paper sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2, flexWrap: 'wrap', gap: 1 }}>
        <Typography variant="h5" gutterBottom sx={{ mb: 0 }}>
          Agents
        </Typography>
        <Button
          variant="contained"
          color="primary"
          startIcon={<AddIcon />}
          onClick={() => setRegisterOpen(true)}
          data-testid="register-agent-button"
        >
          Register Agent
        </Button>
      </Box>

      {admin && (
        <Box sx={{ mb: 2 }}>
          <RegisterAdminKeyPanel
            onSuccess={(did) => setSnackbar(`Admin public key registered for ${did}`)}
          />
        </Box>
      )}

      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>DID</TableCell>
              <TableCell>Name</TableCell>
              <TableCell>Role</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Validators</TableCell>
              <TableCell>Scope</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {agents.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                    No agents registered yet.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              agents.map((agent) => (
                <TableRow
                  key={agent.did}
                  hover
                  onClick={() => setDetailTarget(agent)}
                  sx={{ cursor: 'pointer' }}
                >
                  <TableCell>
                    <Typography variant="body2" sx={{ wordBreak: 'break-all' }}>
                      {agent.did}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" fontWeight="500">
                      {agent.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{agent.role}</Typography>
                  </TableCell>
                  <TableCell>
                    <AgentStatusBadge status={agent.status} />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{agent.validator_count}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{agent.scope || 'public'}</Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'inline-flex', gap: 0.5 }}>
                      <Tooltip title="Quick view">
                        <IconButton
                          size="small"
                          onClick={(event) => {
                            event.stopPropagation();
                            setDetailTarget(agent);
                          }}
                        >
                          <VisibilityIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Validate">
                        <span>
                          <IconButton
                            size="small"
                            disabled={!canDeprecate(agent.status)}
                            onClick={(event) => {
                              event.stopPropagation();
                              setValidateTarget(agent);
                            }}
                          >
                            <ThumbUpIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                      {admin && (
                        <Tooltip title="Admin validate (trust root)">
                          <span>
                            <IconButton
                              size="small"
                              disabled={!canDeprecate(agent.status)}
                              onClick={(event) => {
                                event.stopPropagation();
                                setAdminValidateTarget(agent);
                              }}
                              data-testid={`admin-validate-${agent.did}`}
                            >
                              <VerifiedUserIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      )}
                      <Tooltip title="Deprecate">
                        <span>
                          <IconButton
                            size="small"
                            disabled={!canDeprecate(agent.status)}
                            onClick={(event) => {
                              event.stopPropagation();
                              setDeprecateTarget(agent);
                            }}
                          >
                            <BlockIcon fontSize="small" />
                          </IconButton>
                        </span>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      <TablePagination
        component="div"
        count={total}
        page={page}
        onPageChange={(_, newPage) => setPage(newPage)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={(event) => {
          setRowsPerPage(parseInt(event.target.value, 10));
          setPage(0);
        }}
        rowsPerPageOptions={[5, 10, 20]}
      />

      <RegisterAgentDialog
        open={registerOpen}
        onClose={() => setRegisterOpen(false)}
        onSuccess={() => setSnackbar('Agent registered')}
      />
      <ValidateAgentDialog
        open={validateTarget !== null}
        agent={validateTarget}
        onClose={() => setValidateTarget(null)}
        onSuccess={() => setSnackbar(`Agent ${validateTarget?.did ?? ''} validated`)}
      />
      <AdminValidateDialog
        open={adminValidateTarget !== null}
        agent={adminValidateTarget}
        onClose={() => setAdminValidateTarget(null)}
        onSuccess={() =>
          setSnackbar(`Agent ${adminValidateTarget?.did ?? ''} admin-validated`)
        }
      />
      <ConfirmDialog
        open={deprecateTarget !== null}
        title="Deprecate Agent"
        description={
          deprecateTarget
            ? `Deprecate ${deprecateTarget.name} (${deprecateTarget.did})? This action cannot be undone.`
            : ''
        }
        confirmText="Deprecate"
        onConfirm={handleDeprecateConfirm}
        onCancel={() => setDeprecateTarget(null)}
      />
      <AgentDetailDrawer
        open={detailTarget !== null}
        agent={detailTarget}
        onClose={() => setDetailTarget(null)}
      />
      {deprecateMutation.isError && (
        <Snackbar
          open
          autoHideDuration={5000}
          onClose={() => deprecateMutation.reset()}
          message={errorMessage(deprecateMutation.error, 'Failed to deprecate agent')}
        />
      )}
      <Snackbar
        open={snackbar !== null}
        autoHideDuration={3000}
        onClose={() => setSnackbar(null)}
        message={snackbar ?? undefined}
      />
    </Paper>
  );
}
