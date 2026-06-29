import React from 'react';
import Box from '@mui/material/Box';
import Container from '@mui/material/Container';

interface ResponsiveContainerProps {
  children: React.ReactNode;
  maxWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | false;
}

export function ResponsiveContainer({
  children,
  maxWidth = 'lg',
}: ResponsiveContainerProps): JSX.Element {
  return (
    <Container maxWidth={maxWidth} sx={{ py: 2 }}>
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          gap: 2,
          width: '100%',
        }}
      >
        {children}
      </Box>
    </Container>
  );
}
