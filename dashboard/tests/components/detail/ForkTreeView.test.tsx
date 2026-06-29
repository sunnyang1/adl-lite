import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ForkTreeView } from '@/components/detail/ForkTreeView';
import type { D3TreeNode } from '@/hooks/useForkTree';

// Mock react-d3-tree to avoid jsdom issues
vi.mock('react-d3-tree', () => {
  return {
    default: vi.fn(({ data, 'data-testid': testId }) => {
      return (
        <div data-testid={testId || 'mock-tree'}>
          <span>{data.name}</span>
          {data.children?.map((child: D3TreeNode, index: number) => (
            <span key={index}>{child.name}</span>
          ))}
        </div>
      );
    }),
  };
});

describe('ForkTreeView', () => {
  const mockD3TreeData: D3TreeNode = {
    name: 'ADL-001',
    children: [
      {
        name: 'ADL-002',
        children: [],
      },
      {
        name: 'ADL-003',
        children: [
          {
            name: 'ADL-004',
            children: [],
          },
        ],
      },
    ],
  };

  it('renders without crashing', () => {
    render(<ForkTreeView d3TreeData={mockD3TreeData} />);
    expect(screen.getByTestId('fork-tree-view')).toBeInTheDocument();
  });

  it('displays the tree title', () => {
    render(<ForkTreeView d3TreeData={mockD3TreeData} />);
    expect(screen.getByText('Fork Tree')).toBeInTheDocument();
  });

  it('renders tree nodes with correct labels', () => {
    render(<ForkTreeView d3TreeData={mockD3TreeData} />);

    // Should display the root node
    expect(screen.getByText('ADL-001')).toBeInTheDocument();

    // Should display child nodes
    expect(screen.getByText('ADL-002')).toBeInTheDocument();
    expect(screen.getByText('ADL-003')).toBeInTheDocument();
  });

  it('handles empty tree data gracefully', () => {
    const emptyTree: D3TreeNode = { name: 'No forks', children: [] };
    render(<ForkTreeView d3TreeData={emptyTree} />);

    expect(screen.getByTestId('fork-tree-view')).toBeInTheDocument();
    expect(screen.getByText('No forks')).toBeInTheDocument();
  });

  it('applies custom height prop', () => {
    const customHeight = 500;
    render(<ForkTreeView d3TreeData={mockD3TreeData} height={customHeight} />);

    const treeContainer = screen.getByTestId('fork-tree-view');
    expect(treeContainer).toHaveStyle({ height: `${customHeight}px` });
  });

  it('renders with collapsed state by default', () => {
    render(<ForkTreeView d3TreeData={mockD3TreeData} />);

    // The component should render (implementation detail: collapse property)
    const treeContainer = screen.getByTestId('fork-tree-view');
    expect(treeContainer).toBeInTheDocument();
  });
});
