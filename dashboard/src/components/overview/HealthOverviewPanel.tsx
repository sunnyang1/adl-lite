import { useMemo } from 'react';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import { useCapabilities } from '@/api/endpoints';
import { useMode } from '@/api/endpoints';
import { StatusCard } from '@/components/overview/StatusCard';
import { ModeIndicator } from '@/components/overview/ModeIndicator';
import { HealthStats } from '@/api/types';
import { formatConfidence } from '@/utils/formatters';

export function HealthOverviewPanel(): JSX.Element {
  const { data: capabilitiesData } = useCapabilities(0, 100);
  const { data: modeData } = useMode();

  const stats: HealthStats = useMemo(() => {
    const total: number = capabilitiesData?.total ?? 0;
    const active: number = capabilitiesData?.capabilities?.length ?? 0;
    const deprecated: number = 0;
    const avgConfidence: number = 0;
    const mode = modeData?.mode ?? 'moderate';
    const devMode: boolean = modeData?.dev_mode ?? false;

    return {
      total,
      active,
      deprecated,
      avg_confidence: avgConfidence,
      mode,
      dev_mode: devMode,
    };
  }, [capabilitiesData, modeData]);

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom>
        System Health Overview
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={3}>
          <StatusCard
            label="Total Capabilities"
            value={String(stats.total)}
            icon="📊"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatusCard
            label="Active"
            value={String(stats.active)}
            icon="✅"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatusCard
            label="Deprecated"
            value={String(stats.deprecated)}
            icon="⛔"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatusCard
            label="Avg Confidence"
            value={formatConfidence(stats.avg_confidence)}
            icon="🎯"
          />
        </Grid>
        <Grid item xs={12} sm={6}>
          <ModeIndicator mode={stats.mode} devMode={stats.dev_mode} />
        </Grid>
      </Grid>
    </Paper>
  );
}
