import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { parentApi, type Child } from '@/api/parent';
import { useParentAuthGuard } from '@/hooks/useParentAuthGuard';
import { ChildCard } from '@/components/ChildCard';
import { SubscriptionCard } from '@/components/SubscriptionCard';
import { Button } from '@/components/ui/button';
import { ErrorBanner } from '@/components/ErrorBanner';
import { useToast } from '@/hooks/use-toast';
import { FeedbackDialog } from '@/components/child/FeedbackDialog';
import { SignInMethods } from '@/components/parent/SignInMethods';
import { GroupsCard } from '@/components/parent/GroupsCard';
import { NotificationPreferencesCard } from '@/components/parent/NotificationPreferencesCard';
import { PremiumRequestsCard } from '@/components/parent/PremiumRequestsCard';
import { PremiumValueCard } from '@/components/parent/PremiumValueCard';
import { Penny } from '@/components/child/ui/Penny';

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

  const [feedbackOpen, setFeedbackOpen] = useState(false);
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
      <header className="sticky top-0 z-10 -mx-4 -mt-4 mb-4 flex items-center justify-between border-b border-brand-200 bg-white/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:-mt-6 sm:px-6">
        <div className="flex items-center gap-2">
          <Link to="/parent" className="flex items-center gap-2" aria-label="InvestiKid parent home">
            <Penny size={32} mood="happy" />
            <span className="text-lg font-extrabold tracking-tight text-ink sm:text-xl">InvestiKid</span>
          </Link>
          <h1 className="sr-only">Parent Dashboard</h1>
        </div>
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" onClick={() => setFeedbackOpen(true)}>
            Send Feedback
          </Button>
          <Button variant="ghost" size="sm" onClick={() => logout.mutate()} disabled={logout.isPending}>
            Log out
          </Button>
        </div>
      </header>

      <PremiumRequestsCard
        onApprove={() =>
          document.getElementById('subscription-card')?.scrollIntoView({ behavior: 'smooth' })
        }
      />
      <PremiumValueCard
        onSubscribe={() =>
          document.getElementById('subscription-card')?.scrollIntoView({ behavior: 'smooth' })
        }
      />
      <div id="subscription-card">
        <SubscriptionCard />
      </div>
      <NotificationPreferencesCard />

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
          No children linked to this account yet — once a child signs up with your email, they'll appear here.
        </p>
      )}
      {q.data && q.data.length > 0 && (
        <ul className="mt-6 space-y-3">
          {q.data.map((c: Child) => (
            <li key={c.user_id}><ChildCard child={c} /></li>
          ))}
        </ul>
      )}
      <GroupsCard
        childrenList={(q.data ?? []).map((c: Child) => ({ user_id: c.user_id, username: c.username }))}
      />
      <SignInMethods />
      <FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} audience="parent" />
    </main>
  );
}
