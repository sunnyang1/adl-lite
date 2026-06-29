import { ResponsiveContainer } from '@/components/layout/ResponsiveContainer';
import { CapabilityExplorer } from '@/components/capabilities/CapabilityExplorer';

export function CapabilitiesPage(): JSX.Element {
  return (
    <ResponsiveContainer maxWidth="lg">
      <CapabilityExplorer />
    </ResponsiveContainer>
  );
}
