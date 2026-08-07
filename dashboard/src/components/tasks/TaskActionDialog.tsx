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
  FormControlLabel,
  Switch,
} from '@mui/material';
import { TaskSummary, TaskCloseOutcome } from '@/api/types';
import {
  useTaskClaim,
  useTaskSubmit,
  useTaskValidate,
  useTaskClose,
} from '@/api/endpoints';
import { errorMessage } from '@/utils/errors';

export type TaskActionKind = 'claim' | 'submit' | 'validate' | 'close';

const CLOSE_OUTCOMES: TaskCloseOutcome[] = ['accepted', 'rejected', 'cancelled'];

const KIND_TITLES: Record<TaskActionKind, string> = {
  claim: 'Claim Task',
  submit: 'Submit Result',
  validate: 'Validate Task',
  close: 'Close Task',
};

interface TaskActionDialogProps {
  open: boolean;
  kind: TaskActionKind;
  task: TaskSummary | null;
  onClose: () => void;
  onSuccess?: () => void;
}

export function TaskActionDialog({
  open,
  kind,
  task,
  onClose,
  onSuccess,
}: TaskActionDialogProps): JSX.Element {
  const taskId: string = task?.task_id ?? '';
  const claimMutation = useTaskClaim(taskId);
  const submitMutation = useTaskSubmit(taskId);
  const validateMutation = useTaskValidate(taskId);
  const closeMutation = useTaskClose(taskId);

  const [agentDid, setAgentDid] = useState('');
  const [resultRef, setResultRef] = useState('');
  const [summary, setSummary] = useState('');
  const [confidence, setConfidence] = useState('');
  const [validatorDid, setValidatorDid] = useState('');
  const [accepted, setAccepted] = useState(true);
  const [critique, setCritique] = useState('');
  const [actor, setActor] = useState('admin');
  const [outcome, setOutcome] = useState<TaskCloseOutcome>('accepted');
  const [reason, setReason] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setAgentDid('');
      setResultRef('');
      setSummary('');
      setConfidence('');
      setValidatorDid('');
      setAccepted(true);
      setCritique('');
      setActor('admin');
      setOutcome('accepted');
      setReason('');
      setValidationError(null);
      claimMutation.reset();
      submitMutation.reset();
      validateMutation.reset();
      closeMutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const anySuccess: boolean =
    claimMutation.isSuccess ||
    submitMutation.isSuccess ||
    validateMutation.isSuccess ||
    closeMutation.isSuccess;

  useEffect(() => {
    if (anySuccess) {
      onSuccess?.();
      onClose();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [anySuccess]);

  const busy: boolean =
    claimMutation.isPending ||
    submitMutation.isPending ||
    validateMutation.isPending ||
    closeMutation.isPending;

  const mutationError: unknown =
    claimMutation.error ??
    submitMutation.error ??
    validateMutation.error ??
    closeMutation.error ??
    null;

  const hasMutationError: boolean =
    mutationError !== null && mutationError !== undefined;

  const handleSubmit = (): void => {
    switch (kind) {
      case 'claim': {
        if (!agentDid.trim()) {
          setValidationError('Agent DID is required');
          return;
        }
        claimMutation.mutate({ agent_did: agentDid.trim() });
        break;
      }
      case 'submit': {
        if (!agentDid.trim()) {
          setValidationError('Agent DID is required');
          return;
        }
        if (!resultRef.trim()) {
          setValidationError('Result reference is required');
          return;
        }
        submitMutation.mutate({
          agent_did: agentDid.trim(),
          result_ref: resultRef.trim(),
          summary: summary.trim() || undefined,
          confidence:
            confidence.trim() === '' ? undefined : Number(confidence),
        });
        break;
      }
      case 'validate': {
        if (!validatorDid.trim()) {
          setValidationError('Validator DID is required');
          return;
        }
        validateMutation.mutate({
          validator_did: validatorDid.trim(),
          accepted,
          confidence:
            confidence.trim() === '' ? undefined : Number(confidence),
          critique: critique.trim() || undefined,
        });
        break;
      }
      case 'close': {
        if (!actor.trim()) {
          setValidationError('Actor is required');
          return;
        }
        closeMutation.mutate({
          actor: actor.trim(),
          outcome,
          reason: reason.trim() || undefined,
        });
        break;
      }
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      data-testid="task-action-dialog"
    >
      <DialogTitle>
        {KIND_TITLES[kind]}
        {task ? ` — ${task.task_id}` : ''}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          {kind === 'claim' && (
            <TextField
              label="Agent DID"
              value={agentDid}
              onChange={(e) => setAgentDid(e.target.value)}
              required
              fullWidth
              error={!!validationError}
              helperText={validationError}
            />
          )}

          {kind === 'submit' && (
            <>
              <TextField
                label="Agent DID"
                value={agentDid}
                onChange={(e) => setAgentDid(e.target.value)}
                required
                fullWidth
                error={!!validationError}
                helperText={validationError}
              />
              <TextField
                label="Result Reference"
                value={resultRef}
                onChange={(e) => setResultRef(e.target.value)}
                required
                fullWidth
              />
              <TextField
                label="Summary (optional)"
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                fullWidth
                multiline
                minRows={2}
              />
              <TextField
                label="Confidence (optional)"
                value={confidence}
                onChange={(e) => setConfidence(e.target.value)}
                fullWidth
                type="number"
                inputProps={{ min: 0, max: 1, step: 0.05 }}
                helperText="0 to 1"
              />
            </>
          )}

          {kind === 'validate' && (
            <>
              <TextField
                label="Validator DID"
                value={validatorDid}
                onChange={(e) => setValidatorDid(e.target.value)}
                required
                fullWidth
                error={!!validationError}
                helperText={validationError}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={accepted}
                    onChange={(e) => setAccepted(e.target.checked)}
                  />
                }
                label={accepted ? 'Accepted' : 'Rejected'}
              />
              <TextField
                label="Confidence (optional)"
                value={confidence}
                onChange={(e) => setConfidence(e.target.value)}
                fullWidth
                type="number"
                inputProps={{ min: 0, max: 1, step: 0.05 }}
                helperText="0 to 1"
              />
              <TextField
                label="Critique (optional)"
                value={critique}
                onChange={(e) => setCritique(e.target.value)}
                fullWidth
                multiline
                minRows={2}
              />
            </>
          )}

          {kind === 'close' && (
            <>
              <TextField
                label="Actor"
                value={actor}
                onChange={(e) => setActor(e.target.value)}
                required
                fullWidth
                error={!!validationError}
                helperText={validationError}
              />
              <FormControl fullWidth>
                <InputLabel id="task-close-outcome-label">Outcome</InputLabel>
                <Select
                  labelId="task-close-outcome-label"
                  label="Outcome"
                  value={outcome}
                  onChange={(e: SelectChangeEvent<TaskCloseOutcome>) =>
                    setOutcome(e.target.value as TaskCloseOutcome)
                  }
                >
                  {CLOSE_OUTCOMES.map((option) => (
                    <MenuItem key={option} value={option}>
                      {option}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
              <TextField
                label="Reason (optional)"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                fullWidth
                multiline
                minRows={2}
              />
            </>
          )}
        </Box>

        {hasMutationError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {errorMessage(mutationError, 'Task action failed')}
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
        >
          Confirm
        </Button>
      </DialogActions>
    </Dialog>
  );
}
