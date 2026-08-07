import { ResponsiveContainer } from '@/components/layout/ResponsiveContainer';
import { RuntimeOverview } from '@/components/runtime/RuntimeOverview';

export default function RuntimePage(): JSX.Element {
  return (
    <ResponsiveContainer maxWidth="lg">
      <RuntimeOverview />
    </ResponsiveContainer>
  );
}
