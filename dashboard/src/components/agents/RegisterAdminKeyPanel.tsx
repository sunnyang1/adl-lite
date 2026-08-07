import { useEffect, useState } from 'react';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Box,
  Button,
  TextField,
  Alert,
  Typography,
  CircularProgress,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import { useAdminPublicKey } from '@/api/endpoints';
import { errorMessage } from '@/utils/errors';

interface RegisterAdminKeyPanelProps {
  onSuccess?: (registeredDid: string) => void;
}

/**
 * Collapsible admin-only panel for registering the admin DID public key.
 *
 * Trust-root bootstrap depends on the backend knowing the admin public key
 * (P0-3: API-key ↔ DID-signature binding). The key is a base64-encoded
 * public key pasted by the operator.
 */
export function RegisterAdminKeyPanel({
  onSuccess,
}: RegisterAdminKeyPanelProps): JSX.Element {
  const registerMutation = useAdminPublicKey();

  const [did, setDid] = useState('');
  const [publicKey, setPublicKey] = useState('');
  const [validationError, setValidationError] = useState<string | null>(null);

  useEffect(() => {
    if (!registerMutation.isSuccess) {
      return;
    }
    const registered = registerMutation.data?.registered ?? '';
    onSuccess?.(registered);
    setDid('');
    setPublicKey('');
    setValidationError(null);
    registerMutation.reset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [registerMutation.isSuccess]);

  const handleSubmit = (): void => {
    if (!did.trim()) {
      setValidationError('Admin DID is required');
      return;
    }
    if (!publicKey.trim()) {
      setValidationError('Public key is required (base64)');
      return;
    }
    setValidationError(null);
    registerMutation.mutate({
      did: did.trim(),
      public_key: publicKey.trim(),
    });
  };

  const busy: boolean = registerMutation.isPending;

  return (
    <Accordion data-testid="register-admin-key-panel">
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <VpnKeyIcon fontSize="small" />
          <Typography variant="body1">Register admin public key</Typography>
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Admin DID"
            value={did}
            onChange={(e) => setDid(e.target.value)}
            required
            fullWidth
            error={!!validationError}
            helperText={validationError}
            data-testid="admin-key-did-input"
          />
          <TextField
            label="Public Key (base64)"
            value={publicKey}
            onChange={(e) => setPublicKey(e.target.value)}
            required
            fullWidth
            multiline
            minRows={3}
            error={!!validationError}
            helperText="base64-encoded admin public key"
            data-testid="admin-key-public-key-input"
          />
          <Box>
            <Button
              variant="outlined"
              color="primary"
              startIcon={<VpnKeyIcon />}
              onClick={handleSubmit}
              disabled={busy}
              data-testid="admin-key-register-button"
            >
              Register Key
            </Button>
            {busy && <CircularProgress size={20} sx={{ ml: 2 }} />}
          </Box>
          {registerMutation.isError && (
            <Alert severity="error">
              {errorMessage(registerMutation.error, 'Failed to register admin public key')}
            </Alert>
          )}
          {registerMutation.isSuccess && (
            <Alert severity="success">
              Registered admin public key for {registerMutation.data?.registered} (
              {registerMutation.data?.admin_public_keys} total)
            </Alert>
          )}
        </Box>
      </AccordionDetails>
    </Accordion>
  );
}
