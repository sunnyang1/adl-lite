import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Switch from '@mui/material/Switch';
import FormControlLabel from '@mui/material/FormControlLabel';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import { useTrustDiversity, useToggleTrustDiversity } from '@/api/endpoints';
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton';
import { ErrorAlert } from '@/components/shared/ErrorAlert';
import { errorMessage } from '@/utils/errors';

export function TrustPanel(): JSX.Element {
  const { data, isLoading, error, refetch } = useTrustDiversity();
  const toggleMutation = useToggleTrustDiversity();

  if (isLoading) {
    return <LoadingSkeleton count={2} />;
  }

  if (error) {
    return (
      <ErrorAlert
        message={errorMessage(error, 'Failed to load trust settings')}
        onRetry={refetch}
      />
    );
  }

  const enabled: boolean = data?.diversity_enabled ?? false;

  const handleToggle = (): void => {
    toggleMutation.mutate(!enabled);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <Typography variant="h5" gutterBottom>
        Trust Settings
      </Typography>

      <Paper sx={{ p: 2 }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 1,
          }}
        >
          <Box>
            <Typography variant="h6">B4 Diversity</Typography>
            <Typography variant="body2" color="text.secondary">
              是否启用多样性约束（diversity constraint）
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip label="Admin" size="small" color="secondary" variant="outlined" />
            <FormControlLabel
              control={
                <Switch
                  checked={enabled}
                  onChange={handleToggle}
                  disabled={toggleMutation.isPending}
                  data-testid="diversity-switch"
                />
              }
              label={enabled ? 'Enabled' : 'Disabled'}
            />
            {toggleMutation.isPending && <CircularProgress size={20} />}
          </Box>
        </Box>

        {toggleMutation.isError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {errorMessage(toggleMutation.error, 'Failed to update diversity setting')}
          </Alert>
        )}
      </Paper>

      <Alert severity="info">
        <strong>弱信号声明：</strong>reputation 仅用于排序，禁止用于安全准入决策。
        信任分数是弱信号，不能作为访问控制或安全边界的依据。
      </Alert>
    </Box>
  );
}
