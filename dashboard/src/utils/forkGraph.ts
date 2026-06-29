import { EventDict, ForkTreeNode } from '@/api/types';

interface D3TreeNode {
  name: string;
  children: D3TreeNode[];
}

/**
 * Build a fork tree (adjacency structure) from event payloads.
 *
 * Each event may contain fork information in its payload, indicating
 * that a capability was forked from the current one.
 *
 * @param adlId - The root capability ID
 * @param events - Array of events to scan for fork references
 * @returns A ForkTreeNode representing the root with children from fork events
 */
export function buildForkGraph(
  adlId: string,
  events: EventDict[],
): ForkTreeNode {
  const root: ForkTreeNode = {
    adl_id: adlId,
    event_type: 'root',
    children: [],
  };

  for (const event of events) {
    if (event.event_type === 'fork') {
      const forkedAdlId: string =
        (event.payload?.forked_adl_id as string) ?? '';

      if (forkedAdlId) {
        root.children.push({
          adl_id: forkedAdlId,
          event_type: 'fork',
          children: [],
        });
      }
    }
  }

  return root;
}

/**
 * Convert a ForkTreeNode to a format suitable for react-d3-tree.
 *
 * react-d3-tree expects nodes with `name` and `children` fields.
 *
 * @param node - ForkTreeNode to convert
 * @returns Object compatible with react-d3-tree's Tree component
 */
export function toD3TreeFormat(node: ForkTreeNode): D3TreeNode {
  return {
    name: node.adl_id,
    children: node.children.map((child: ForkTreeNode) => toD3TreeFormat(child)),
  };
}
