import { ChangeEvent } from 'react';
import Box from '@mui/material/Box';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import InputAdornment from '@mui/material/InputAdornment';
import SearchIcon from '@mui/icons-material/Search';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import { useSelectionStore } from '@/store/useSelectionStore';
import { AdlStatus } from '@/api/types';

const STATUS_OPTIONS: { value: AdlStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All Statuses' },
  { value: 'provisional', label: 'Provisional 🟡' },
  { value: 'validated', label: 'Validated 🟢' },
  { value: 'deprecated', label: 'Deprecated 🔴' },
  { value: 'forked', label: 'Forked 🔵' },
  { value: 'archived', label: 'Archived ⚪' },
];

export function CapabilitySearchBar(): JSX.Element {
  const searchQuery = useSelectionStore((state) => state.searchQuery);
  const setSearchQuery = useSelectionStore((state) => state.setSearchQuery);
  const statusFilter = useSelectionStore((state) => state.statusFilter);
  const setStatusFilter = useSelectionStore((state) => state.setStatusFilter);

  return (
    <Box sx={{ display: 'flex', gap: 2, mb: 2, alignItems: 'center' }}>
      <TextField
        size="small"
        placeholder="Search capabilities..."
        value={searchQuery}
        onChange={(e: ChangeEvent<HTMLInputElement>) =>
          setSearchQuery(e.target.value)
        }
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          ),
        }}
        sx={{ flexGrow: 1 }}
      />
      <FormControl size="small" sx={{ minWidth: 160 }}>
        <InputLabel>Status</InputLabel>
        <Select
          value={statusFilter}
          label="Status"
          onChange={(e) =>
            setStatusFilter(e.target.value as AdlStatus | 'all')
          }
        >
          {STATUS_OPTIONS.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Box>
  );
}
