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
import type { AdlStatus } from '@/api/types';

interface TransitionDialogProps {
  open: boolean;
  adlId: string;
  onClose: () => void;
  onSuccess?: () => void;
}

const STATUS_OPTIONS: AdlStatus[] = ['validated', 'deprecated', 'archived'];

export const TransitionDialog: React.FC<TransitionDialogProps> = ({
  open,
  adlId,
  onClose,
  onSuccess,
}) => {
  const [toStatus, setToStatus] = useState<AdlStatus | ''>('');
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
    setToStatus('');
    setReason('');
    setActor('user');
    setError(null);
    setValidationError(null);
  };

  const handleSubmit = async () => {
    // Validate
    if (!toStatus) {
      setValidationError('Please select a status');
      return;
    }
    
    setValidationError(null);
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/consensus/transition', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          adl_id: adlId,
          to_status: toStatus,
          actor: actor || 'user',
          reason: reason || '',
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || errorData.error || `Failed to transition: ${response.status}`
        );
      }
      
      resetForm();
      onSuccess?.();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to transition status');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} data-testid="transition-dialog" maxWidth="sm" fullWidth>
      <DialogTitle>Transition Status</DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <Typography variant="body2" color="text.secondary">
            Capability: <strong>{adlId}</strong>
          </Typography>
          
          <TextField
            select
            label="New Status"
            value={toStatus}
            onChange={(e) => setToStatus(e.target.value as AdlStatus)}
            fullWidth
            error={!!validationError}
            helperText={validationError}
            SelectProps={{ native: true }}
            data-testid="status-select"
          >
            <option value="">Select a status</option>
            {STATUS_OPTIONS.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </TextField>
          
          <TextField
            label="Actor"
            value={actor}
            onChange={(e) => setActor(e.target.value)}
            fullWidth
            helperText="Actor performing the transition"
          />
          
          <TextField
            label="Reason"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            fullWidth
            multiline
            rows={3}
            helperText="Reason for the transition (optional)"
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
          data-testid="transition-submit-button"
        >
          Transition
        </Button>
      </DialogActions>
    </Dialog>
  );
};
