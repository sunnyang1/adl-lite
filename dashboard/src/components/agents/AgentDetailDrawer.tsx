import Drawer from '@mui/material/Drawer';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { useNavigate } from 'react-router-dom';
import { Agent } from '@/api/types';
import { AgentProfilePanel } from '@/components/agents/AgentProfilePanel';

interface AgentDetailDrawerProps {
  open: boolean;
  agent: Agent | null;
  onClose: () => void;
}

export function AgentDetailDrawer({
  open,
  agent,
  onClose,
}: AgentDetailDrawerProps): JSX.Element {
  const navigate = useNavigate();
  const did: string = agent?.did ?? '';

  const handleOpenPage = (): void => {
    onClose();
    navigate(`/agents/${did}`);
  };

  return (
    <Drawer
      anchor="right"
      open={open}
      onClose={onClose}
      data-testid="agent-detail-drawer"
      PaperProps={{ sx: { width: { xs: '100%', sm: 440 } } }}
    >
      <Box sx={{ p: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Typography variant="h6" fontWeight="bold">
            Agent Detail
          </Typography>
          <Button
            size="small"
            endIcon={<OpenInNewIcon />}
            onClick={handleOpenPage}
            disabled={!did}
          >
            Open page
          </Button>
        </Box>
        <AgentProfilePanel did={did} />
      </Box>
    </Drawer>
  );
}
