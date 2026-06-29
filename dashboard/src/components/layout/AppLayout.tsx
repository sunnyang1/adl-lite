import React from 'react';
import Box from '@mui/material/Box';
import { AppSidebar } from '@/components/layout/AppSidebar';
import { AppHeader } from '@/components/layout/AppHeader';
import { ErrorBoundary } from '@/components/shared/ErrorBoundary';

interface AppLayoutProps {
  children: React.ReactNode;
}

export function AppLayout({ children }: AppLayoutProps): JSX.Element {
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <AppSidebar />
      <Box sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
        <AppHeader />
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: 3,
            bgcolor: 'background.default',
            overflow: 'auto',
          }}
        >
          <ErrorBoundary>
            <>{children}</>
          </ErrorBoundary>
        </Box>
      </Box>
    </Box>
  );
}
