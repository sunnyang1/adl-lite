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

interface ForkDialogProps {
  open: boolean;
  originalId: string;
  onClose: () => void;
  onSuccess?: () => void;
}

export const ForkDialog: React.FC<ForkDialogProps> = ({
  open,
  originalId,
  onClose,
  onSuccess,
}) => {
  const [forkId, setForkId] = useState('');
  const [reason, setReason] = useState('');
  const [actor, setActor] = useState('user');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleClose = () => {
    resetForm();
    onClose();
  };

  const resetForm = () => {
    setForkId('');
    setReason('');
    setActor('user');
    setError(null);
    setValidationError(null);
  };

  const handleSubmit = async () => {
    // Validate
    if (!forkId.trim()) {
      setValidationError('Fork ID is required');
      return;
    }
    
    setValidationError(null);
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/consensus/fork', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          original_id: originalId,
          fork_id: forkId.trim(),
          actor: actor || 'user',
          reason: reason || '',
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || errorData.error || `Failed to fork: ${response.status}`
        );
      }
      
      resetForm();
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create fork');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} data-testid="fork-dialog" maxWidth="sm" fullWidth>
      <DialogTitle>Create Fork</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Original Capability: <strong>{originalId}</strong>
          </Typography>
          
          <TextField
            label="Fork ID"
            value={forkId}
            onChange={(e) => setForkId(e.target.value)}
            fullWidth
            required
            error={!!validationError}
            helperText={validationError}
            data-testid="fork-id-input"
          />
          
          <TextField
            label="Actor"
            value={actor}
            onChange={(e) => setActor(e.target.value)}
            fullWidth
            helperText="Actor creating the fork"
          />
          
          <TextField
            label="Reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            fullWidth
            multiline
            rows={3}
            helperText="Reason for the fork (optional)"
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
          data-testid="fork-submit-button"
        >
          Create Fork
        </Button>
      </DialogActions>
    </Dialog>
  );
};
