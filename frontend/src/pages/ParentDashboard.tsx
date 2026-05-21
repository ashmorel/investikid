import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useEffect } from 'react';
import { parentApi, type Child } from '@/api/parent';
import { useParentAuthGuard } from '@/hooks/useParentAuthGuard';
import { ChildCard } from '@/components/ChildCard';
import { SubscriptionCard } from '@/components/SubscriptionCard';
import { Button } from '@/components/ui/button';
import { ErrorBanner } from '@/components/ErrorBanner';
import { useToast } from '@/hooks/use-toast';

export default function ParentDashboard() {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['children'], queryFn: parentApi.listChildren });
  useParentAuthGuard(q.error);

  const logout = useMutation({
    mutationFn: parentApi.logout,
    onSettled: () => {
      qc.removeQueries({ queryKey: ['children'] });
      navigate('/parent/login', { replace: true });
    },
  });

  const [searchParams, setSearchParams] = useSearchParams();
  const { toast } = useToast();

  useEffect(() => {
    const checkoutResult = searchParams.get('checkout');
    if (checkoutResult === 'success') {
      toast({
        title: 'Welcome to Premium!',
        description: 'All your children now have access to premium features.',
      });
      searchParams.delete('checkout');
      setSearchParams(searchParams, { replace: true });
    } else if (checkoutResult === 'canceled') {
      searchParams.delete('checkout');
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams, toast]);

  return (
    <main className="mx-auto max-w-2xl px-4 py-4 sm:px-6 sm:py-6">
      <header className="sticky top-0 z-10 -mx-4 -mt-4 mb-4 flex items-center justify-between border-b border-amber-200 bg-white/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:-mt-6 sm:px-6">
        <div className="flex items-center gap-2">
          <Link to="/parent" className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-orange-500 text-sm font-extrabold text-white">
            IE
          </Link>
          <h1 className="text-lg font-semibold sm:text-2xl">Parent Dashboard</h1>
        </div>
        <Button variant="ghost" size="sm" onClick={() => logout.mutate()} disabled={logout.isPending}>
          Log out
        </Button>
      </header>

      <SubscriptionCard />

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
