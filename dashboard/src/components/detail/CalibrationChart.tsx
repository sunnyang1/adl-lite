import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from 'recharts';
import { Typography } from '@mui/material';
import type { EwmaPoint } from '@/api/types';

interface CalibrationChartProps {
  ewmaPoints: EwmaPoint[];
  height?: number;
  width?: number;
}

export function CalibrationChart({ ewmaPoints, height = 300, width = 600 }: CalibrationChartProps) {
  if (ewmaPoints.length === 0) {
    return (
      <div data-testid="calibration-chart" style={{ height: `${height}px`, width: `${width}px` }}>
        <Typography variant="h6">EWMA Calibration Curve</Typography>
        <Typography color="textSecondary">No calibration data available</Typography>
      </div>
    );
  }

  return (
    <div data-testid="calibration-chart" style={{ height: `${height}px`, width: `${width}px` }}>
      <Typography variant="h6" gutterBottom>EWMA Calibration Curve</Typography>
      <LineChart data={ewmaPoints} width={width} height={height - 50}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="timestamp"
          tickFormatter={(value: string) => new Date(value).toLocaleDateString()}
        />
        <YAxis domain={[0, 1]} />
        <Tooltip />
        <Legend />
        <Line
          type="monotone"
          dataKey="raw"
          stroke="#8884d8"
          name="Raw Confidence"
          dot={{ r: 4 }}
        />
        <Line
          type="monotone"
          dataKey="smoothed"
          stroke="#82ca9d"
          name="EWMA Smoothed"
          dot={{ r: 4 }}
        />
      </LineChart>
    </div>
  );
}
