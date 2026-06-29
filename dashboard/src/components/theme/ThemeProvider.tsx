import React from 'react';
import { ThemeProvider as MuiThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { useThemeStore } from '@/store/useThemeStore';
import { createAppTheme } from '@/components/theme/theme';

export function AppThemeProvider({
  children,
}: {
  children: React.ReactNode;
}): JSX.Element {
  const mode = useThemeStore((state) => state.mode);
  const theme = createAppTheme(mode);

  return (
    <MuiThemeProvider theme={theme}>
      <CssBaseline />
      {children}
    </MuiThemeProvider>
  );
}
