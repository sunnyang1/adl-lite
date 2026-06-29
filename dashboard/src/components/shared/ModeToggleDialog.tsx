import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Alert,
  CircularProgress,
} from '@mui/material';
import { useModeStore } from '@/store/useModeStore';

interface ModeToggleDialogProps {
  open: boolean;
  onClose: () => void;
}

export const ModeToggleDialog: React.FC<ModeToggleDialogProps> = ({ open, onClose }) => {
  const { devMode, setMode } = useModeStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSwitchToDev = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/consensus/mode/dev', {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to switch to dev mode: ${response.status}`);
      }
      
      const data = await response.json();
      setMode(data.mode, data.n_min, data.dev_mode);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to switch to dev mode');
    } finally {
      setLoading(false);
    }
  };

  const handleSwitchToProduction = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/v1/consensus/mode/production', {
        method: 'POST',
      });
      
      if (!response.ok) {
        throw new Error(`Failed to switch to production mode: ${response.status}`);
      }
      
      const data = await response.json();
      setMode(data.mode, data.n_min, data.dev_mode);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to switch to production mode');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleCancel} data-testid="mode-toggle-dialog">
      <DialogTitle>Toggle System Mode</DialogTitle>
      <DialogContent>
        <Box sx={{ mb: 2 }}>
          <Typography variant="body1" gutterBottom>
            Current Mode: <strong>{devMode ? 'Dev' : 'Production'}</strong>
          </Typography>
          <Typography variant="body2" color="text.secondary">
            N Min: {useModeStore.getState().nMin}
          </Typography>
        </Box>
        
        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}
        
        {loading && (
          <Box display="flex" justifyContent="center" sx={{ mb: 2 }}>
            <CircularProgress size={24} />
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleCancel} disabled={loading}>
          Cancel
        </Button>
        {!devMode && (
          <Button
            onClick={handleSwitchToDev}
            variant="contained"
            color="primary"
            disabled={loading}
            data-testid="switch-to-dev-button"
          >
            Switch to Dev
          </Button>
        )}
        {devMode && (
          <Button
            onClick={handleSwitchToProduction}
            variant="contained"
            color="secondary"
            disabled={loading}
            data-testid="switch-to-production-button"
          >
            Switch to Production
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};
