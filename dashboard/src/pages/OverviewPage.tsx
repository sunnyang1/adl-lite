import { ResponsiveContainer } from '@/components/layout/ResponsiveContainer';
import { HealthOverviewPanel } from '@/components/overview/HealthOverviewPanel';

export function OverviewPage(): JSX.Element {
  return (
    <ResponsiveContainer maxWidth="lg">
      <HealthOverviewPanel />
    </ResponsiveContainer>
  );
}
