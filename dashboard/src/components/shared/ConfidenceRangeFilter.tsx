import React from 'react';
import {
  Box,
  Typography,
  Slider,
  Button,
  Paper,
} from '@mui/material';
import { useSelectionStore } from '@/store/useSelectionStore';

interface ConfidenceRangeFilterProps {
  height?: number;
}

export const ConfidenceRangeFilter: React.FC<ConfidenceRangeFilterProps> = ({ height = 80 }) => {
  const { confidenceRange, setConfidenceRange } = useSelectionStore();

  const handleChange = (_event: Event, newValue: number | number[]) => {
    if (Array.isArray(newValue) && newValue.length === 2) {
      setConfidenceRange([newValue[0], newValue[1]]);
    }
  };

  const handleReset = () => {
    setConfidenceRange([0, 1]);
  };

  return (
    <Paper
      data-testid="confidence-range-filter"
      sx={{ p: 2, height: `${height}px` }}
    >
      <Typography variant="subtitle2" gutterBottom>
        Confidence Range Filter
      </Typography>
      <Box sx={{ px: 2 }}>
        <Slider
          value={confidenceRange}
          onChange={handleChange}
          valueLabelDisplay="auto"
          min={0}
          max={1}
          step={0.01}
          marks={[
            { value: 0, label: 'Min' },
            { value: 1, label: 'Max' },
          ]}
          sx={{ mt: 2 }}
        />
      </Box>
      <Box display="flex" justifyContent="space-between" sx={{ mt: 1 }}>
        <Typography variant="caption" color="text.secondary" data-testid="range-display">
          Current: [{confidenceRange[0].toFixed(2)}, {confidenceRange[1].toFixed(2)}]
        </Typography>
        <Button size="small" onClick={handleReset} data-testid="reset-button">
          Reset
        </Button>
      </Box>
    </Paper>
  );
};
