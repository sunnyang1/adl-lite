import Box from '@mui/material/Box';
import ListItem from '@mui/material/ListItem';
import ListItemText from '@mui/material/ListItemText';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import { ValidatorVote } from '@/api/types';
import { formatTimestamp } from '@/utils/formatters';

interface ValidatorVoteRowProps {
  vote: ValidatorVote;
}

export function ValidatorVoteRow({ vote }: ValidatorVoteRowProps): JSX.Element {
  return (
    <ListItem sx={{ px: 0 }}>
      <ListItemText
        primary={
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Chip label={vote.validator} size="small" variant="outlined" />
            <Typography variant="caption" color="text.secondary">
              {formatTimestamp(vote.timestamp)}
            </Typography>
          </Box>
        }
        secondary={vote.reasoning}
      />
    </ListItem>
  );
}
