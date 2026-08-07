import { useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Badge from '@mui/material/Badge';
import Chip from '@mui/material/Chip';
import Button from '@mui/material/Button';
import Tooltip from '@mui/material/Tooltip';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import RefreshIcon from '@mui/icons-material/Refresh';
import SettingsIcon from '@mui/icons-material/Settings';
import LogoutIcon from '@mui/icons-material/Logout';
import LoginIcon from '@mui/icons-material/Login';
import { useThemeStore } from '@/store/useThemeStore';
import { useMode } from '@/api/endpoints';
import { useModeStore } from '@/store/useModeStore';
import { useAuthStore, isAdminUser } from '@/store/authStore';
import { ModeIndicator } from '@/components/overview/ModeIndicator';
import { ModeToggleDialog } from '@/components/shared/ModeToggleDialog';
import { LoginDialog } from '@/components/auth/LoginDialog';
import { formatRelativeTime } from '@/utils/formatters';

export function AppHeader(): JSX.Element {
  const themeMode = useThemeStore((state) => state.mode);
  const toggleTheme = useThemeStore((state) => state.toggleTheme);
  const { data: modeData, refetch, isRefetching } = useMode();
  const setMode = useModeStore((state) => state.setMode);
  const token = useAuthStore((state) => state.token);
  const user = useAuthStore((state) => state.user);
  const logout = useAuthStore((state) => state.logout);
  const [modeToggleOpen, setModeToggleOpen] = useState(false);
  const [loginOpen, setLoginOpen] = useState(false);

  const signedIn: boolean = token !== null && user !== null;
  const admin: boolean = isAdminUser(user);

  useEffect(() => {
    if (modeData) {
      setMode(modeData.mode, modeData.n_min, modeData.dev_mode);
    }
  }, [modeData, setMode]);

  const handleRefresh = (): void => {
    refetch();
  };

  const lastUpdated: string = modeData
    ? formatRelativeTime(new Date().toISOString())
    : '—';

  return (
    <>
      <AppBar
        position="sticky"
        elevation={1}
        sx={{ bgcolor: 'background.paper', color: 'text.primary' }}
      >
        <Toolbar variant="dense" sx={{ gap: 1 }}>
          <ModeIndicator
            mode={modeData?.mode ?? 'moderate'}
            devMode={modeData?.dev_mode ?? false}
          />
          <Chip
            label={`N_min: ${modeData?.n_min ?? '—'}`}
            size="small"
            variant="outlined"
          />
          <Typography
            variant="body2"
            sx={{ ml: 1, color: 'text.secondary', display: { xs: 'none', md: 'block' } }}
          >
            Updated: {lastUpdated}
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          {signedIn ? (
            <>
              <Chip
                label={user?.identity ?? 'user'}
                size="small"
                color={admin ? 'secondary' : 'default'}
                variant={admin ? 'filled' : 'outlined'}
                data-testid="auth-user-chip"
              />
              {admin && (
                <Chip
                  label="admin"
                  size="small"
                  color="secondary"
                  data-testid="auth-admin-badge"
                />
              )}
              <Tooltip title="Sign out">
                <IconButton
                  onClick={logout}
                  aria-label="sign out"
                  data-testid="auth-logout-button"
                >
                  <LogoutIcon />
                </IconButton>
              </Tooltip>
            </>
          ) : (
            <Button
              size="small"
              variant="outlined"
              startIcon={<LoginIcon />}
              onClick={() => setLoginOpen(true)}
              data-testid="auth-signin-button"
            >
              Sign in
            </Button>
          )}
          <IconButton
            onClick={handleRefresh}
            disabled={isRefetching}
            aria-label="refresh"
          >
            <Badge color="primary" variant="dot" invisible={!isRefetching}>
              <RefreshIcon />
            </Badge>
          </IconButton>
          <IconButton onClick={toggleTheme} aria-label="toggle theme">
            {themeMode === 'dark' ? <LightModeIcon /> : <DarkModeIcon />}
          </IconButton>
          <IconButton
            onClick={() => setModeToggleOpen(true)}
            aria-label="toggle mode"
            color="inherit"
          >
            <SettingsIcon />
          </IconButton>
        </Toolbar>
      </AppBar>
      <ModeToggleDialog
        open={modeToggleOpen}
        onClose={() => setModeToggleOpen(false)}
      />
      <LoginDialog open={loginOpen} onClose={() => setLoginOpen(false)} />
    </>
  );
}
