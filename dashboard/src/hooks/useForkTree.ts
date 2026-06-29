import { useMemo } from 'react';
import { buildForkGraph, toD3TreeFormat } from '@/utils/forkGraph';
import { EventDict, ForkTreeNode } from '@/api/types';

export interface D3TreeNode {
  name: string;
  children: D3TreeNode[];
}

/**
 * Build a fork tree from capability history events.
 *
 * Scans the event list for fork events and constructs a tree structure
 * suitable for visualization with react-d3-tree.
 *
 * @param adlId - The root capability ID
 * @param events - Array of events to scan
 * @returns Object containing the ForkTreeNode root and d3-compatible tree data
 */
export function useForkTree(
  adlId: string,
  events: EventDict[],
): {
  forkTree: ForkTreeNode;
  d3TreeData: D3TreeNode;
} {
  const forkTree = useMemo(
    () => buildForkGraph(adlId, events),
    [adlId, events],
  );

  const d3TreeData: D3TreeNode = useMemo(
    () => toD3TreeFormat(forkTree),
    [forkTree],
  );

  return { forkTree, d3TreeData };
}
