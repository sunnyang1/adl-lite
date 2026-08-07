import { ResponsiveContainer } from '@/components/layout/ResponsiveContainer';
import { AgentExplorer } from '@/components/agents/AgentExplorer';

export default function AgentsPage(): JSX.Element {
  return (
    <ResponsiveContainer maxWidth="lg">
      <AgentExplorer />
    </ResponsiveContainer>
  );
}
