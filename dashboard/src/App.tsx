import { AppLayout } from '@/components/layout/AppLayout';
import { AppRouter } from '@/router';

function App(): JSX.Element {
  return (
    <AppLayout>
      <AppRouter />
    </AppLayout>
  );
}

export default App;
