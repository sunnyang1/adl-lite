import { Component, ErrorInfo, ReactNode } from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Paper from '@mui/material/Paper';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    this.setState({
      error,
      errorInfo,
    });
  }

  handleReset = (): void => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  render(): ReactNode {
    const { hasError, error, errorInfo } = this.state;
    const { children, fallback } = this.props;

    if (hasError) {
      if (fallback) {
        return fallback;
      }

      const isDevelopment = import.meta.env.DEV || import.meta.env.MODE === 'development';

      return (
        <Box
          display="flex"
          justifyContent="center"
          alignItems="center"
          minHeight="100vh"
          p={3}
        >
          <Paper
            elevation={3}
            sx={{
              p: 4,
              maxWidth: 600,
              width: '100%',
            }}
          >
            <Typography variant="h5" color="error" gutterBottom>
              Something went wrong
            </Typography>

            <Typography variant="body1" color="text.secondary" paragraph>
              An unexpected error has occurred. Please try again or contact support if the problem persists.
            </Typography>

            {isDevelopment && error && (
              <Box
                mt={2}
                p={2}
                bgcolor="grey.100"
                borderRadius={1}
                overflow="auto"
              >
                <Typography variant="subtitle2" color="error" gutterBottom>
                  Error Details (Development Mode):
                </Typography>
                <Typography
                  variant="body2"
                  component="pre"
                  sx={{
                    fontSize: '0.75rem',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word',
                  }}
                >
                  {error.toString()}
                </Typography>
                {errorInfo && (
                  <Typography
                    variant="body2"
                    component="pre"
                    sx={{
                      fontSize: '0.75rem',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      mt: 1,
                    }}
                  >
                    {errorInfo.componentStack}
                  </Typography>
                )}
              </Box>
            )}

            <Box mt={3}>
              <Button
                variant="contained"
                color="primary"
                onClick={this.handleReset}
              >
                Try again
              </Button>
            </Box>
          </Paper>
        </Box>
      );
    }

    return children;
  }
}
