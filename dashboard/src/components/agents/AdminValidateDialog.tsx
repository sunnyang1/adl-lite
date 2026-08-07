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
import { useAgentAdminValidate } from '@/api/endpoints';
import { errorMessage } from '@/utils/errors';

interface AdminValidateDialogProps {
  open: boolean;
  agent: Agent | null;
  onClose: () => void;
  onSuccess?: () => void;
}

/**
 * Trust-root bootstrap dialog: an admin signs the target agent's hash.
 *
 * The signature is generated offline with the admin private key and pasted
 * here as a base64 string. The backend verifies it against the admin public
 * key registered via `POST /api/v1/admin/public-key`.
 */
export function AdminValidateDialog({
  open,
  agent,
  onClose,
  onSuccess,
}: AdminValidateDialogProps): JSX.Element {
  const did: string = agent?.did ?? '';
  const adminValidateMutation = useAgentAdminValidate(did);

  const [validatorDid, setValidatorDid] = useState('');
  const [signature, setSignature] = useState('');
  const [reason, setReason] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) {
      setValidatorDid('');
      setSignature('');
      setReason('');
      setValidationError(null);
      adminValidateMutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (adminValidateMutation.isSuccess) {
      onSuccess?.();
      onClose();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [adminValidateMutation.isSuccess]);

  const handleSubmit = (): void => {
    if (!validatorDid.trim()) {
      setValidationError('Admin validator DID is required');
      return;
    }
    if (!signature.trim()) {
      setValidationError('Signature is required (base64, generated offline)');
      return;
    }
    setValidationError(null);
    adminValidateMutation.mutate({
      validator_did: validatorDid.trim(),
      signature: signature.trim(),
      reason: reason.trim() || undefined,
    });
  };

  const busy: boolean = adminValidateMutation.isPending;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      data-testid="admin-validate-dialog"
    >
      <DialogTitle>
        Admin Validate{agent ? ` — ${agent.name}` : ''}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <Alert severity="info" sx={{ mt: 0 }}>
            Admin bootstrap validation: the signature below is generated
            offline with the admin private key (base64 string).
          </Alert>
          <TextField
            label="Admin Validator DID"
            value={validatorDid}
            onChange={(e) => setValidatorDid(e.target.value)}
            required
            fullWidth
            error={!!validationError}
            helperText={validationError}
            data-testid="admin-validator-did-input"
          />
          <TextField
            label="Signature (base64)"
            value={signature}
            onChange={(e) => setSignature(e.target.value)}
            required
            fullWidth
            multiline
            minRows={3}
            error={!!validationError}
            helperText="由 admin 私钥离线生成（base64）"
            data-testid="admin-signature-input"
          />
          <TextField
            label="Reason (optional)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            fullWidth
            multiline
            minRows={2}
          />
        </Box>

        {adminValidateMutation.isError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {errorMessage(adminValidateMutation.error, 'Admin validation failed')}
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
          data-testid="admin-validate-submit-button"
        >
          Admin Validate
        </Button>
      </DialogActions>
    </Dialog>
  );
}
