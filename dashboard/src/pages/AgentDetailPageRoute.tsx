import Box from '@mui/material/Box';
import Breadcrumbs from '@mui/material/Breadcrumbs';
import Link from '@mui/material/Link';
import Typography from '@mui/material/Typography';
import { useParams, useNavigate } from 'react-router-dom';
import { ResponsiveContainer } from '@/components/layout/ResponsiveContainer';
import { AgentProfilePanel } from '@/components/agents/AgentProfilePanel';

export default function AgentDetailPageRoute(): JSX.Element {
  const { did } = useParams<{ did: string }>();
  const navigate = useNavigate();

  return (
    <ResponsiveContainer maxWidth="md">
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Breadcrumbs sx={{ mb: 1 }}>
          <Link
            underline="hover"
            color="inherit"
            onClick={() => navigate('/agents')}
            sx={{ cursor: 'pointer' }}
          >
            Agents
          </Link>
          <Typography color="text.primary">{did}</Typography>
        </Breadcrumbs>
        <AgentProfilePanel did={did ?? ''} />
      </Box>
    </ResponsiveContainer>
  );
}
