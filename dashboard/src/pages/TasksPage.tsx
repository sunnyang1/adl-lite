import { ResponsiveContainer } from '@/components/layout/ResponsiveContainer';
import { TaskExplorer } from '@/components/tasks/TaskExplorer';

export default function TasksPage(): JSX.Element {
  return (
    <ResponsiveContainer maxWidth="lg">
      <TaskExplorer />
    </ResponsiveContainer>
  );
}
