import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import List from '@mui/material/List';
import { useValidatorDetail } from '@/hooks/useValidatorDetail';
import { useHistory } from '@/api/endpoints';
import { ValidatorVoteRow } from '@/components/detail/ValidatorVoteRow';
import { ConfidenceGauge } from '@/components/overview/ConfidenceGauge';
import { useModeStore } from '@/store/useModeStore';
import { formatConfidence } from '@/utils/formatters';

interface ConsensusDetailPanelProps {
  validators: string[];
  confidence: number;
  adlId: string;
}

export function ConsensusDetailPanel({
  validators,
  confidence,
  adlId,
}: ConsensusDetailPanelProps): JSX.Element {
  const nMin = useModeStore((state) => state.nMin);
  const { data: historyData } = useHistory(adlId);
  const votes = useValidatorDetail(historyData?.events ?? []);
  const currentCount: number = validators.length;

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Box sx={{ display: 'flex', gap: 3 }}>
        {/* Confidence gauge */}
        <ConfidenceGauge confidence={confidence} size={100} />

        {/* Consensus info */}
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="h6" gutterBottom>
            Consensus Status
          </Typography>
          <Typography variant="body1">
            Validators: <strong>{currentCount}/{nMin}</strong> required
          </Typography>
          <Typography variant="body1">
            Confidence: <strong>{formatConfidence(confidence)}</strong>
          </Typography>

          {/* Validator votes */}
          {votes.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Validator Votes
              </Typography>
              <List dense>
                {votes.map((vote) => (
                  <ValidatorVoteRow key={vote.event_id} vote={vote} />
                ))}
              </List>
            </Box>
          )}
        </Box>
      </Box>
    </Paper>
  );
}
