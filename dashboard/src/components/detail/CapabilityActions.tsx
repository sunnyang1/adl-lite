import React, { useState } from 'react';
import { Button, Box } from '@mui/material';
import { ModeToggleDialog } from '@/components/shared/ModeToggleDialog';
import { RegisterDialog } from '@/components/shared/RegisterDialog';
import { TransitionDialog } from '@/components/shared/TransitionDialog';
import { ForkDialog } from '@/components/shared/ForkDialog';

interface CapabilityActionsProps {
  adlId: string;
}

export const CapabilityActions: React.FC<CapabilityActionsProps> = ({ adlId }) => {
  const [modeToggleOpen, setModeToggleOpen] = useState(false);
  const [registerOpen, setRegisterOpen] = useState(false);
  const [transitionOpen, setTransitionOpen] = useState(false);
  const [forkOpen, setForkOpen] = useState(false);

  return (
    <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
      <Button
        variant="outlined"
        color="secondary"
        onClick={() => setModeToggleOpen(true)}
        data-testid="toggle-mode-button"
      >
        Toggle Mode
      </Button>
      
      <Button
        variant="outlined"
        color="primary"
        onClick={() => setRegisterOpen(true)}
        data-testid="register-button"
      >
        Register
      </Button>
      
      <Button
        variant="outlined"
        color="info"
        onClick={() => setTransitionOpen(true)}
        data-testid="transition-button"
      >
        Transition
      </Button>
      
      <Button
        variant="outlined"
        color="warning"
        onClick={() => setForkOpen(true)}
        data-testid="fork-button"
      >
        Fork
      </Button>

      <ModeToggleDialog
        open={modeToggleOpen}
        onClose={() => setModeToggleOpen(false)}
      />
      
      <RegisterDialog
        open={registerOpen}
        onClose={() => setRegisterOpen(false)}
      />
      
      <TransitionDialog
        open={transitionOpen}
        adlId={adlId}
        onClose={() => setTransitionOpen(false)}
      />
      
      <ForkDialog
        open={forkOpen}
        originalId={adlId}
        onClose={() => setForkOpen(false)}
      />
    </Box>
  );
};
