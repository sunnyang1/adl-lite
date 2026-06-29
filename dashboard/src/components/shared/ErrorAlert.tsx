import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Button from '@mui/material/Button';

interface ErrorAlertProps {
  message: string;
  onRetry?: () => void;
  severity?: 'error' | 'warning' | 'info';
}

export function ErrorAlert({
  message,
  onRetry,
  severity = 'error',
}: ErrorAlertProps): JSX.Element {
  return (
    <Alert
      severity={severity}
      action={
        onRetry ? (
          <Button color="inherit" size="small" onClick={onRetry}>
            Retry
          </Button>
        ) : undefined
      }
    >
      <AlertTitle>Error</AlertTitle>
      {message}
    </Alert>
  );
}
