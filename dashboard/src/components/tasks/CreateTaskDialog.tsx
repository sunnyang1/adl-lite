import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Alert,
  CircularProgress,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  SelectChangeEvent,
} from '@mui/material';
import { useTaskCreate } from '@/api/endpoints';
import { errorMessage } from '@/utils/errors';

/** Backend expects an int: 0=low, 1=medium, 2=high (list sorts by -priority) */
const PRIORITY_OPTIONS: { value: number; label: string }[] = [
  { value: 0, label: 'low' },
  { value: 1, label: 'medium' },
  { value: 2, label: 'high' },
];

interface CreateTaskDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function CreateTaskDialog({
  open,
  onClose,
  onSuccess,
}: CreateTaskDialogProps): JSX.Element {
  const createMutation = useTaskCreate();

  const [objective, setObjective] = useState('');
  const [capabilities, setCapabilities] = useState('');
  const [priority, setPriority] = useState(1);
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setObjective('');
      setCapabilities('');
      setPriority(1);
      setValidationError(null);
      createMutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (createMutation.isSuccess) {
      onSuccess?.();
      onClose();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [createMutation.isSuccess]);

  const handleSubmit = (): void => {
    if (!objective.trim()) {
      setValidationError('Objective is required');
      return;
    }
    setValidationError(null);
    createMutation.mutate({
      objective: objective.trim(),
      capabilities: capabilities
        .split(',')
        .map((cap) => cap.trim())
        .filter(Boolean),
      priority,
      created_by: 'admin',
    });
  };

  const busy: boolean = createMutation.isPending;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      data-testid="create-task-dialog"
    >
      <DialogTitle>Create Task</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField
            label="Objective"
            value={objective}
            onChange={(e) => setObjective(e.target.value)}
            required
            fullWidth
            multiline
            minRows={2}
            error={!!validationError}
            helperText={validationError}
            data-testid="task-objective-input"
          />
          <TextField
            label="Capabilities (comma-separated)"
            value={capabilities}
            onChange={(e) => setCapabilities(e.target.value)}
            fullWidth
            helperText="Required capabilities, e.g. web_search, code_review"
          />
          <FormControl fullWidth>
            <InputLabel id="task-priority-label">Priority</InputLabel>
            <Select
              labelId="task-priority-label"
              label="Priority"
              value={priority}
              onChange={(e: SelectChangeEvent<number>) =>
                setPriority(Number(e.target.value))
              }
            >
              {PRIORITY_OPTIONS.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Box>

        {createMutation.isError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {errorMessage(createMutation.error, 'Failed to create task')}
          </Alert>
        )}

        {busy && (
          <Box display="flex" justifyContent="center" sx={{ mt: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={busy}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          color="primary"
          disabled={busy}
          data-testid="create-task-submit-button"
        >
          Create
        </Button>
      </DialogActions>
    </Dialog>
  );
}
