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
} from '@mui/material';
import { Agent } from '@/api/types';
import { useAgentValidate } from '@/api/endpoints';
import { errorMessage } from '@/utils/errors';

interface ValidateAgentDialogProps {
  open: boolean;
  agent: Agent | null;
  onClose: () => void;
  onSuccess?: () => void;
}

export function ValidateAgentDialog({
  open,
  agent,
  onClose,
  onSuccess,
}: ValidateAgentDialogProps): JSX.Element {
  const did: string = agent?.did ?? '';
  const validateMutation = useAgentValidate(did);

  const [validatorDid, setValidatorDid] = useState('');
  const [reason, setReason] = useState('');
  const [confidence, setConfidence] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setValidatorDid('');
      setReason('');
      setConfidence('');
      setValidationError(null);
      validateMutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (validateMutation.isSuccess) {
      onSuccess?.();
      onClose();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [validateMutation.isSuccess]);

  const handleSubmit = (): void => {
    if (!validatorDid.trim()) {
      setValidationError('Validator DID is required');
      return;
    }
    setValidationError(null);
    validateMutation.mutate({
      validator_did: validatorDid.trim(),
      reason: reason.trim() || undefined,
      confidence: confidence.trim() === '' ? undefined : Number(confidence),
    });
  };

  const busy: boolean = validateMutation.isPending;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      data-testid="validate-agent-dialog"
    >
      <DialogTitle>Validate Agent{agent ? ` — ${agent.name}` : ''}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField
            label="Validator DID"
            value={validatorDid}
            onChange={(e) => setValidatorDid(e.target.value)}
            required
            fullWidth
            error={!!validationError}
            helperText={validationError}
          />
          <TextField
            label="Reason (optional)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
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
        </Box>

        {validateMutation.isError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {errorMessage(validateMutation.error, 'Failed to validate agent')}
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
          Validate
        </Button>
      </DialogActions>
    </Dialog>
  );
}
