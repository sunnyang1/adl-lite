import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
} from '@mui/material';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  description: string;
  onConfirm: () => void;
  onCancel: () => void;
  confirmText?: string;
  cancelText?: string;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  open,
  title,
  description,
  onConfirm,
  onCancel,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
}) => {
  const handleClose = (_event: object, reason: string) => {
    if (reason === 'backdropClick' || reason === 'escapeKeyDown') {
      onCancel();
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      data-testid="confirm-dialog"
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Typography variant="body1">{description}</Typography>
      </DialogContent>
      <DialogActions>
        <Button onClick={onCancel} data-testid="cancel-button">
          {cancelText}
        </Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          color="primary"
          data-testid="confirm-button"
        >
          {confirmText}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
