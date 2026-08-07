import { useEffect, useMemo, useState } from 'react';
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
import { AgentRole } from '@/api/types';
import { useAgentRegister, useRoles } from '@/api/endpoints';
import { errorMessage } from '@/utils/errors';

/** Hardcoded fallback roles when `/api/v1/meta/roles` is unavailable. */
const FALLBACK_ROLE_OPTIONS: AgentRole[] = [
  'discoverer',
  'reviewer',
  'skeptic',
  'merger',
  'librarian',
  'planner',
];

interface RegisterAgentDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export function RegisterAgentDialog({
  open,
  onClose,
  onSuccess,
}: RegisterAgentDialogProps): JSX.Element {
  const registerMutation = useAgentRegister();
  const rolesQuery = useRoles(open);

  const [name, setName] = useState('');
  const [role, setRole] = useState<AgentRole>('discoverer');
  const [scope, setScope] = useState('public');
  const [did, setDid] = useState('');
  const [model, setModel] = useState('');
  const [capabilities, setCapabilities] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  // Role options come from the backend meta endpoint when available,
  // otherwise fall back to the hardcoded role list.
  const roleOptions: AgentRole[] = useMemo(() => {
    const metaRoles = rolesQuery.data?.roles;
    if (metaRoles && Object.keys(metaRoles).length > 0) {
      return Object.keys(metaRoles) as AgentRole[];
    }
    return FALLBACK_ROLE_OPTIONS;
  }, [rolesQuery.data]);

  // Keep the selected role valid when the option list changes.
  useEffect(() => {
    if (roleOptions.length > 0 && !roleOptions.includes(role)) {
      setRole(roleOptions[0] ?? 'discoverer');
    }
  }, [roleOptions, role]);

  const resetForm = (): void => {
    setName('');
    setRole('discoverer');
    setScope('public');
    setDid('');
    setModel('');
    setCapabilities('');
    setValidationError(null);
  };

  // Reset the form + mutation whenever the dialog visibility changes
  useEffect(() => {
    if (!open) {
      resetForm();
      registerMutation.reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (registerMutation.isSuccess) {
      onSuccess?.();
      onClose();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [registerMutation.isSuccess]);

  const handleClose = (): void => {
    onClose();
  };

  const handleSubmit = (): void => {
    if (!name.trim()) {
      setValidationError('Name is required');
      return;
    }
    setValidationError(null);
    registerMutation.mutate({
      name: name.trim(),
      role,
      scope: scope.trim() || undefined,
      did: did.trim() || undefined,
      model: model.trim() || undefined,
      capabilities: capabilities
        .split(',')
        .map((cap) => cap.trim())
        .filter(Boolean),
    });
  };

  const busy: boolean = registerMutation.isPending;

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      data-testid="register-agent-dialog"
    >
      <DialogTitle>Register Agent</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField
            label="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            fullWidth
            error={!!validationError}
            helperText={validationError}
            data-testid="agent-name-input"
          />
          <FormControl fullWidth>
            <InputLabel id="agent-role-label">Role</InputLabel>
            <Select
              labelId="agent-role-label"
              label="Role"
              value={role}
              onChange={(e: SelectChangeEvent<AgentRole>) =>
                setRole(e.target.value as AgentRole)
              }
            >
              {roleOptions.map((option) => (
                <MenuItem key={option} value={option}>
                  {option}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            label="Scope"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            fullWidth
            helperText="Visibility scope (default: public)"
          />
          <TextField
            label="DID (optional)"
            value={did}
            onChange={(e) => setDid(e.target.value)}
            fullWidth
            helperText="Leave empty to auto-generate"
          />
          <TextField
            label="Model (optional)"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            fullWidth
          />
          <TextField
            label="Capabilities (comma-separated)"
            value={capabilities}
            onChange={(e) => setCapabilities(e.target.value)}
            fullWidth
            helperText="e.g. web_search, code_review"
          />
        </Box>

        {registerMutation.isError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {errorMessage(registerMutation.error, 'Failed to register agent')}
          </Alert>
        )}

        {busy && (
          <Box display="flex" justifyContent="center" sx={{ mt: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={busy}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          color="primary"
          disabled={busy}
          data-testid="register-agent-submit-button"
        >
          Register
        </Button>
      </DialogActions>
    </Dialog>
  );
}
