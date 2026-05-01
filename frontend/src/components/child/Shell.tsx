import { Outlet } from 'react-router-dom';
import { useChildSession } from '@/hooks/useChildSession';
import { useChildAuthGuard } from '@/hooks/useChildAuthGuard';
import { TopNav } from './TopNav';

export function Shell() {
  const session = useChildSession();
  useChildAuthGuard(session.error);

  if (session.isLoading) {
    return (
      <div className="min-h-screen">
        <header className="h-14 border-b" aria-busy="true" />
        <p className="mx-auto mt-6 max-w-2xl px-4 text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }

  if (!session.data) {
    return null;
  }

  return (
    <div className="min-h-screen">
      <TopNav username={session.data.username} />
      <main>
        <Outlet />
      </main>
    </div>
  );
}
