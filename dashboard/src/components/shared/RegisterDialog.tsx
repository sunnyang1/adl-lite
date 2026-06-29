import React, { useState } from 'react';
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
  Typography,
} from '@mui/material';

interface RegisterDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

export const RegisterDialog: React.FC<RegisterDialogProps> = ({ open, onClose, onSuccess }) => {
  const [adlId, setAdlId] = useState('');
  const [scope, setScope] = useState('public');
  const [domain, setDomain] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const resetForm = () => {
    setAdlId('');
    setScope('public');
    setDomain('');
    setError(null);
    setValidationError(null);
  };

  const handleSubmit = async () => {
    // Validate
    if (!adlId.trim()) {
      setValidationError('ADL ID is required');
      return;
    }
    
    setValidationError(null);
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/consensus/register', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          adl_id: adlId.trim(),
          scope: scope || 'public',
          domain: domain || '',
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || errorData.error || `Failed to register: ${response.status}`
        );
      }
      
      resetForm();
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to register capability');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} data-testid="register-dialog" maxWidth="sm" fullWidth>
      <DialogTitle>Register New Capability</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField
            label="ADL ID"
            value={adlId}
            onChange={(e) => setAdlId(e.target.value)}
            required
            fullWidth
            error={!!validationError}
            helperText={validationError}
            data-testid="adl-id-input"
          />
          
          <TextField
            label="Scope"
            value={scope}
            onChange={(e) => setScope(e.target.value)}
            fullWidth
            helperText="Visibility scope (default: public)"
          />
          
          <TextField
            label="Domain"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            fullWidth
            helperText="Domain tag (optional)"
          />
        </Box>
        
        {error && (
          <Alert severity="error" sx={{ mt: 2 }} data-testid="error-alert">
            {error}
          </Alert>
        )}
        
        {loading && (
          <Box display="flex" justifyContent="center" sx={{ mt: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          color="primary"
          disabled={loading}
          data-testid="register-submit-button"
        >
          Register
        </Button>
      </DialogActions>
    </Dialog>
  );
};
