import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { parentApi, type Child } from '@/api/parent';
import { useAuthGuard } from '@/hooks/useAuthGuard';
import { ChildCard } from '@/components/ChildCard';
import { Button } from '@/components/ui/button';
import { ErrorBanner } from '@/components/ErrorBanner';

export default function ParentDashboard() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['children'], queryFn: parentApi.listChildren });
  useAuthGuard(q.error);

  const logout = useMutation({
    mutationFn: parentApi.logout,
    onSettled: () => {
      qc.removeQueries({ queryKey: ['children'] });
      navigate('/parent/login', { replace: true });
    },
  });

  return (
    <main className="mx-auto max-w-2xl p-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Parent dashboard</h1>
        <Button variant="ghost" onClick={() => logout.mutate()} disabled={logout.isPending}>
          Log out
        </Button>
      </header>

      {q.isLoading && <p className="mt-6 text-sm text-muted-foreground">Loading…</p>}
      {q.isError && (
        <ErrorBanner
          className="mt-6"
          title="Could not load children"
          message="Please try refreshing the page."
        />
      )}
      {q.data && q.data.length === 0 && (
        <p className="mt-6 text-sm text-muted-foreground">
          No children linked to this account.
        </p>
      )}
      {q.data && q.data.length > 0 && (
        <ul className="mt-6 space-y-3">
          {q.data.map((c: Child) => (
            <li key={c.user_id}><ChildCard child={c} /></li>
          ))}
        </ul>
      )}
    </main>
  );
}
