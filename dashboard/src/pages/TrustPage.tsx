import { ResponsiveContainer } from '@/components/layout/ResponsiveContainer';
import { TrustPanel } from '@/components/runtime/TrustPanel';

export default function TrustPage(): JSX.Element {
  return (
    <ResponsiveContainer maxWidth="lg">
      <TrustPanel />
    </ResponsiveContainer>
  );
}
