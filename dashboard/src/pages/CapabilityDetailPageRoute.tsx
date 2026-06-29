import { ResponsiveContainer } from '@/components/layout/ResponsiveContainer';
import { CapabilityDetailPage } from '@/components/detail/CapabilityDetailPage';

export default function CapabilityDetailPageRoute(): JSX.Element {
  return (
    <ResponsiveContainer maxWidth="md">
      <CapabilityDetailPage />
    </ResponsiveContainer>
  );
}
