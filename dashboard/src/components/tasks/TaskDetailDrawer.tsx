import Drawer from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import { useTask } from '@/api/endpoints';
import { TaskSummary } from '@/api/types';
import { TaskStatusBadge } from '@/components/tasks/TaskStatusBadge';
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton';
import { ErrorAlert } from '@/components/shared/ErrorAlert';
import { errorMessage } from '@/utils/errors';

interface TaskDetailDrawerProps {
  open: boolean;
  task: TaskSummary | null;
  onClose: () => void;
}

export function TaskDetailDrawer({
  open,
  task,
  onClose,
}: TaskDetailDrawerProps): JSX.Element {
  const taskId: string = task?.task_id ?? '';
  const { data, isLoading, error, refetch } = useTask(taskId);

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      data-testid="task-detail-drawer"
      PaperProps={{ sx: { width: { xs: '100%', sm: 440 } } }}
    >
      <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Typography variant="h6" fontWeight="bold">
          Task Detail
        </Typography>

        {isLoading ? (
          <LoadingSkeleton count={3} />
        ) : error ? (
          <ErrorAlert
            message={errorMessage(error, 'Failed to load task')}
            onRetry={refetch}
          />
        ) : !data ? (
          <ErrorAlert message={`Task not found: ${taskId}`} />
        ) : (
          <>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
              <Typography variant="h6">{data.task_id}</Typography>
              <TaskStatusBadge status={data.status} />
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Objective
              </Typography>
              <Typography variant="body1">{data.objective}</Typography>
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Required Capabilities
              </Typography>
              {data.required_capabilities.length === 0 ? (
                <Typography variant="body2" color="text.secondary">
                  None
                </Typography>
              ) : (
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  {data.required_capabilities.map((cap) => (
                    <Chip key={cap} label={cap} size="small" variant="outlined" />
                  ))}
                </Stack>
              )}
            </Box>
            <Box>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                Result Reference
              </Typography>
              <Typography variant="body1" sx={{ wordBreak: 'break-all' }}>
                {data.result_ref || '—'}
              </Typography>
            </Box>
          </>
        )}
      </Box>
    </Drawer>
  );
}
