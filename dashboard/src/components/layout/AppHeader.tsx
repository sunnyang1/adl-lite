import { useEffect, useState } from 'react';
import Box from '@mui/material/Box';
import AppBar from '@mui/material/AppBar';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import IconButton from '@mui/material/IconButton';
import Badge from '@mui/material/Badge';
import Chip from '@mui/material/Chip';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import RefreshIcon from '@mui/icons-material/Refresh';
import SettingsIcon from '@mui/icons-material/Settings';
import { useThemeStore } from '@/store/useThemeStore';
import { useMode } from '@/api/endpoints';
import { useModeStore } from '@/store/useModeStore';
import { ModeIndicator } from '@/components/overview/ModeIndicator';
import { ModeToggleDialog } from '@/components/shared/ModeToggleDialog';
import { formatRelativeTime } from '@/utils/formatters';

export function AppHeader(): JSX.Element {
  const themeMode = useThemeStore((state) => state.mode);
  const toggleTheme = useThemeStore((state) => state.toggleTheme);
  const { data: modeData, refetch, isRefetching } = useMode();
  const setMode = useModeStore((state) => state.setMode);
  const [modeToggleOpen, setModeToggleOpen] = useState(false);

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
        <Toolbar variant="dense" sx={{ gap: 2 }}>
          <ModeIndicator
            mode={modeData?.mode ?? 'moderate'}
            devMode={modeData?.dev_mode ?? false}
          />
          <Chip
            label={`N_min: ${modeData?.n_min ?? '—'}`}
            size="small"
            variant="outlined"
          />
          <Typography variant="body2" sx={{ ml: 1, color: 'text.secondary' }}>
            Updated: {lastUpdated}
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
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
    </>
  );
}
