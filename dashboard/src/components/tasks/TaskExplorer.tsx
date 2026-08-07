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
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import AddIcon from '@mui/icons-material/Add';
import { useTasks, useTaskTransitions } from '@/api/endpoints';
import { TaskStatus, TaskSummary } from '@/api/types';
import { availableTaskActions } from '@/utils/taskActions';
import { TaskStatusBadge } from '@/components/tasks/TaskStatusBadge';
import { CreateTaskDialog } from '@/components/tasks/CreateTaskDialog';
import { TaskActionDialog, TaskActionKind } from '@/components/tasks/TaskActionDialog';
import { TaskDetailDrawer } from '@/components/tasks/TaskDetailDrawer';
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton';
import { ErrorAlert } from '@/components/shared/ErrorAlert';

const STATUS_OPTIONS: { value: TaskStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All Statuses' },
  { value: 'open', label: 'Open' },
  { value: 'assigned', label: 'Assigned' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'validated', label: 'Validated' },
  { value: 'rejected', label: 'Rejected' },
  { value: 'closed', label: 'Closed' },
];

const ACTION_LABELS: Record<TaskActionKind, string> = {
  claim: 'Claim',
  submit: 'Submit',
  validate: 'Validate',
  close: 'Close',
};

const PRIORITY_LABELS: Record<number, string> = {
  0: 'low',
  1: 'medium',
  2: 'high',
};

/** Render the numeric priority as a human label (0=low, 1=medium, 2=high) */
function priorityLabel(priority: number | null | undefined): string {
  if (priority === undefined || priority === null) {
    return '—';
  }
  return PRIORITY_LABELS[priority] ?? String(priority);
}

export function TaskExplorer(): JSX.Element {
  const [statusFilter, setStatusFilter] = useState<TaskStatus | 'all'>('all');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);

  const [createOpen, setCreateOpen] = useState(false);
  const [action, setAction] = useState<{
    kind: TaskActionKind;
    task: TaskSummary;
  } | null>(null);
  const [detailTarget, setDetailTarget] = useState<TaskSummary | null>(null);
  const [snackbar, setSnackbar] = useState<string | null>(null);

  const { data, isLoading, error, refetch } = useTasks(
    statusFilter,
    page * rowsPerPage,
    rowsPerPage,
  );

  // Backend state machine as the single source of truth for legal actions.
  // Falls back to the hardcoded mapping while loading or when the endpoint
  // is unavailable, so existing behavior never regresses.
  const transitionsQuery = useTaskTransitions();

  const tasks: TaskSummary[] = data?.tasks ?? [];
  const total: number = data?.total ?? 0;

  if (isLoading) {
    return <LoadingSkeleton count={6} />;
  }

  if (error) {
    return <ErrorAlert message="Failed to load tasks" onRetry={refetch} />;
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 2,
          flexWrap: 'wrap',
          gap: 1,
        }}
      >
        <Typography variant="h5" gutterBottom sx={{ mb: 0 }}>
          Tasks
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
          <FormControl size="small" sx={{ minWidth: 160 }}>
            <InputLabel id="task-status-filter-label">Status</InputLabel>
            <Select
              labelId="task-status-filter-label"
              label="Status"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value as TaskStatus | 'all');
                setPage(0);
              }}
            >
              {STATUS_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setCreateOpen(true)}
            data-testid="create-task-button"
          >
            Create Task
          </Button>
        </Box>
      </Box>

      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Task ID</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Objective</TableCell>
              <TableCell>Priority</TableCell>
              <TableCell>Result Ref</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {tasks.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} align="center">
                  <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
                    No tasks found.
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              tasks.map((task) => (
                <TableRow
                  key={task.task_id}
                  hover
                  onClick={() => setDetailTarget(task)}
                  sx={{ cursor: 'pointer' }}
                >
                  <TableCell>
                    <Typography variant="body2" fontWeight="500">
                      {task.task_id}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <TaskStatusBadge status={task.status} />
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant="body2"
                      noWrap
                      sx={{ maxWidth: 280 }}
                      title={task.objective}
                    >
                      {task.objective}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {priorityLabel(task.priority)}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography
                      variant="body2"
                      noWrap
                      sx={{ maxWidth: 160 }}
                      title={task.result_ref ?? ''}
                    >
                      {task.result_ref || '—'}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Box sx={{ display: 'inline-flex', gap: 0.5 }}>
                      {availableTaskActions(
                        task.status,
                        transitionsQuery.data?.transitions ?? null,
                      ).map((kind) => (
                        <Button
                          key={kind}
                          size="small"
                          variant="outlined"
                          onClick={(event) => {
                            event.stopPropagation();
                            setAction({ kind, task });
                          }}
                        >
                          {ACTION_LABELS[kind]}
                        </Button>
                      ))}
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

      <CreateTaskDialog
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onSuccess={() => setSnackbar('Task created')}
      />
      <TaskActionDialog
        open={action !== null}
        kind={action?.kind ?? 'claim'}
        task={action?.task ?? null}
        onClose={() => setAction(null)}
        onSuccess={() =>
          setSnackbar(`${action?.kind ?? 'Task'} action succeeded`)
        }
      />
      <TaskDetailDrawer
        open={detailTarget !== null}
        task={detailTarget}
        onClose={() => setDetailTarget(null)}
      />
      <Snackbar
        open={snackbar !== null}
        autoHideDuration={3000}
        onClose={() => setSnackbar(null)}
        message={snackbar ?? undefined}
      />
    </Paper>
  );
}
