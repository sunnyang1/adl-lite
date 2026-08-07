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
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import { useLogin, probeAuthStatus } from '@/api/endpoints';
import { errorMessage } from '@/utils/errors';

type LoginMode = 'credentials' | 'apiKey';

interface LoginDialogProps {
  open: boolean;
  onClose: () => void;
}

/** Text shown when the backend runs with auth disabled (demo mode). */
export const DEMO_MODE_HINT =
  '当前为 demo 模式（auth 关闭），登录不影响数据面';

/**
 * Sign-in dialog.
 *
 * Supports two credential modes:
 * - Username + password (the password is the API key in the OAuth2 flow).
 * - API key only (same endpoint, username is a fixed placeholder).
 *
 * On open the dialog probes `/api/v1/auth/token` once to detect demo mode
 * (auth disabled → 400). A failed login with the same 400 status also reveals
 * the demo-mode hint, covering backends that reject the probe differently.
 */
export function LoginDialog({ open, onClose }: LoginDialogProps): JSX.Element {
  const loginMutation = useLogin();

  const [mode, setMode] = useState<LoginMode>('credentials');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [demoMode, setDemoMode] = useState<boolean | null>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    setMode('credentials');
    setUsername('');
    setPassword('');
    setApiKey('');
    setValidationError(null);
    setDemoMode(null);
    loginMutation.reset();
    // One lightweight probe to surface demo mode (auth disabled).
    let cancelled = false;
    probeAuthStatus()
      .then((status) => {
        if (!cancelled) {
          setDemoMode(status === 'disabled');
        }
      })
      .catch(() => {
        if (!cancelled) {
          setDemoMode(null);
        }
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  useEffect(() => {
    if (loginMutation.isSuccess) {
      onClose();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [loginMutation.isSuccess]);

  const isAuthDisabledError: boolean =
    loginMutation.isError &&
    (loginMutation.error as { status_code?: number } | null)?.status_code === 400;

  const handleSubmit = (): void => {
    if (mode === 'credentials') {
      if (!username.trim() || !password) {
        setValidationError('Username and password are required');
        return;
      }
      setValidationError(null);
      loginMutation.mutate({ username: username.trim(), password });
    } else {
      if (!apiKey.trim()) {
        setValidationError('API key is required');
        return;
      }
      setValidationError(null);
      loginMutation.mutate({ username: 'api-key', password: apiKey.trim() });
    }
  };

  const busy: boolean = loginMutation.isPending;

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      data-testid="login-dialog"
    >
      <DialogTitle>Sign in</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          {(demoMode === true || isAuthDisabledError) && (
            <Alert severity="info" data-testid="demo-mode-hint">
              {DEMO_MODE_HINT}
            </Alert>
          )}

          <ToggleButtonGroup
            exclusive
            fullWidth
            size="small"
            value={mode}
            onChange={(_, next: LoginMode | null) => {
              if (next) {
                setMode(next);
                setValidationError(null);
              }
            }}
          >
            <ToggleButton value="credentials" data-testid="login-mode-credentials">
              Username / Password
            </ToggleButton>
            <ToggleButton value="apiKey" data-testid="login-mode-apikey">
              API Key
            </ToggleButton>
          </ToggleButtonGroup>

          {mode === 'credentials' && (
            <>
              <TextField
                label="Username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                fullWidth
                autoFocus
                error={!!validationError}
                helperText={validationError}
                data-testid="login-username-input"
              />
              <TextField
                label="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                fullWidth
                type="password"
                error={!!validationError}
                helperText="API key or account password"
                data-testid="login-password-input"
              />
            </>
          )}

          {mode === 'apiKey' && (
            <TextField
              label="API Key"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              required
              fullWidth
              type="password"
              autoFocus
              error={!!validationError}
              helperText={validationError}
              data-testid="login-apikey-input"
            />
          )}
        </Box>

        {loginMutation.isError && !isAuthDisabledError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {errorMessage(loginMutation.error, 'Sign in failed')}
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
          data-testid="login-submit-button"
        >
          Sign in
        </Button>
      </DialogActions>
    </Dialog>
  );
}
