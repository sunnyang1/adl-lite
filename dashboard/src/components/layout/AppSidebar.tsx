import Drawer from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Typography from '@mui/material/Typography';
import DashboardIcon from '@mui/icons-material/Dashboard';
import ChecklistIcon from '@mui/icons-material/Checklist';
import RecommendIcon from '@mui/icons-material/Recommend';
import AssignmentIcon from '@mui/icons-material/Assignment';
import SpeedIcon from '@mui/icons-material/Speed';
import GppGoodIcon from '@mui/icons-material/GppGood';
import { useNavigate, useLocation } from 'react-router-dom';

const DRAWER_WIDTH = 240;

const NAV_ITEMS = [
  { label: 'Overview', path: '/overview', icon: <DashboardIcon /> },
  { label: 'Capabilities', path: '/capabilities', icon: <ChecklistIcon /> },
  { label: 'Agents', path: '/agents', icon: <RecommendIcon /> },
  { label: 'Tasks', path: '/tasks', icon: <AssignmentIcon /> },
  { label: 'Runtime', path: '/runtime', icon: <SpeedIcon /> },
  { label: 'Trust', path: '/trust', icon: <GppGoodIcon /> },
];

export function AppSidebar(): JSX.Element {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: DRAWER_WIDTH,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
        },
      }}
    >
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <Typography variant="h6" fontWeight="bold" color="primary">
          ADL Lite
        </Typography>
      </Box>
      <List>
        {NAV_ITEMS.map((item) => {
          const isActive: boolean =
            location.pathname === item.path ||
            location.pathname.startsWith(`${item.path}/`);
          return (
            <ListItem key={item.path} disablePadding>
              <ListItemButton
                selected={isActive}
                onClick={() => navigate(item.path)}
                sx={{
                  '&.Mui-selected': {
                    bgcolor: 'primary.light',
                    '&:hover': { bgcolor: 'primary.light' },
                  },
                }}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </Drawer>
  );
}
