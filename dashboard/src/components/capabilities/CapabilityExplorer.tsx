import { useState, useMemo } from 'react';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import TablePagination from '@mui/material/TablePagination';
import { useCapabilities } from '@/api/endpoints';
import { CapabilitySummary, AdlStatus } from '@/api/types';
import { CapabilityRow } from '@/components/capabilities/CapabilityRow';
import { CapabilitySearchBar } from '@/components/capabilities/CapabilitySearchBar';
import { ConfidenceRangeFilter } from '@/components/shared/ConfidenceRangeFilter';
import { useSelectionStore } from '@/store/useSelectionStore';
import { LoadingSkeleton } from '@/components/shared/LoadingSkeleton';
import { ErrorAlert } from '@/components/shared/ErrorAlert';

export function CapabilityExplorer(): JSX.Element {
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const searchQuery = useSelectionStore((state) => state.searchQuery);
  const statusFilter = useSelectionStore((state) => state.statusFilter);
  const confidenceRange = useSelectionStore((state) => state.confidenceRange);

  const {
    data: capabilitiesData,
    isLoading,
    error,
    refetch,
  } = useCapabilities(page * rowsPerPage, rowsPerPage);

  const capabilities: string[] = capabilitiesData?.capabilities ?? [];
  const total: number = capabilitiesData?.total ?? 0;

  const summaries: CapabilitySummary[] = useMemo(() => {
    return capabilities.map((adlId: string) => ({
      adl_id: adlId,
      status: 'provisional' as AdlStatus,
      confidence: 0,
      validators: [],
      validator_count: 0,
      confidence_color: 'low',
    }));
  }, [capabilities]);

  const filteredSummaries: CapabilitySummary[] = useMemo(() => {
    let filtered = summaries;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter((s: CapabilitySummary) =>
        s.adl_id.toLowerCase().includes(query),
      );
    }

    if (statusFilter !== 'all') {
      filtered = filtered.filter(
        (s: CapabilitySummary) => s.status === statusFilter,
      );
    }

    // Filter by confidence range
    filtered = filtered.filter(
      (s: CapabilitySummary) =>
        s.confidence >= confidenceRange[0] && s.confidence <= confidenceRange[1],
    );

    return filtered;
  }, [summaries, searchQuery, statusFilter, confidenceRange]);

  if (isLoading) {
    return <LoadingSkeleton count={5} />;
  }

  if (error) {
    return <ErrorAlert message="Failed to load capabilities" onRetry={refetch} />;
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h5" gutterBottom>
        Capability Explorer
      </Typography>
      <CapabilitySearchBar />
      <ConfidenceRangeFilter />
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>ID</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Confidence</TableCell>
              <TableCell>Validators</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredSummaries.map((summary: CapabilitySummary) => (
              <CapabilityRow key={summary.adl_id} summary={summary} />
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <TablePagination
        component="div"
        count={total}
        page={page}
        onPageChange={(_, newPage) => setPage(newPage)}
        rowsPerPage={rowsPerPage}
        onRowsPerPageChange={(event) => {
          setRowsPerPage(parseInt(event.target.value, 10));
          setPage(0);
        }}
        rowsPerPageOptions={[5, 10, 20]}
      />
    </Paper>
  );
}
