import React from 'react';
import Tree from 'react-d3-tree';
import { Typography, Paper } from '@mui/material';
import type { D3TreeNode } from '@/hooks/useForkTree';

interface ForkTreeViewProps {
  d3TreeData: D3TreeNode;
  height?: number;
}

export function ForkTreeView({ d3TreeData, height = 400 }: ForkTreeViewProps) {
  return (
    <Paper 
      data-testid="fork-tree-view" 
      style={{ height: `${height}px`, padding: '16px' }}
      elevation={1}
    >
      <Typography variant="h6" gutterBottom>
        Fork Tree
      </Typography>
      <div style={{ height: `${height - 100}px`, width: '100%', overflow: 'auto' }}>
        <Tree
          data={d3TreeData}
          orientation="vertical"
          collapsible={true}
          initialDepth={0}
        />
      </div>
    </Paper>
  );
}
