import { useState } from 'react';
import { ResponsiveContainer } from '@/components/layout/ResponsiveContainer';
import { HealthOverviewPanel } from '@/components/overview/HealthOverviewPanel';
import { RegisterDialog } from '@/components/shared/RegisterDialog';
import { TransitionDialog } from '@/components/shared/TransitionDialog';
import Paper from '@mui/material/Paper';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import AddIcon from '@mui/icons-material/Add';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';

export function OverviewPage(): JSX.Element {
  const [registerOpen, setRegisterOpen] = useState(false);
  const [transitionOpen, setTransitionOpen] = useState(false);

  return (
    <ResponsiveContainer maxWidth="lg">
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          <Button
            variant="contained"
            color="primary"
            startIcon={<AddIcon />}
            onClick={() => setRegisterOpen(true)}
            data-testid="quick-register-button"
          >
            Register New Capability
          </Button>
          <Button
            variant="outlined"
            color="secondary"
            startIcon={<SwapHorizIcon />}
            onClick={() => setTransitionOpen(true)}
            data-testid="quick-transition-button"
          >
            Transition Status
          </Button>
        </Box>
      </Paper>
      <HealthOverviewPanel />
      <RegisterDialog
        open={registerOpen}
        onClose={() => setRegisterOpen(false)}
      />
      <TransitionDialog
        open={transitionOpen}
        adlId=""
        onClose={() => setTransitionOpen(false)}
      />
    </ResponsiveContainer>
  );
}
