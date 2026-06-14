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
import { MasteryReportCard } from '@/components/parent/MasteryReportCard';
import { PremiumValueCard } from '@/components/parent/PremiumValueCard';
import { DeleteAccountCard } from '@/components/parent/DeleteAccountCard';
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
  const [hintSeen, setHintSeen] = useState(() => localStorage.getItem('parent-welcome-seen') === '1');
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
      <header
        className="sticky top-0 z-10 -mx-4 -mt-4 mb-4 flex items-center justify-between border-b border-brand-200 bg-white/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:-mt-6 sm:px-6"
        style={{ paddingTop: 'calc(env(safe-area-inset-top, 0px) + 0.75rem)' }}
      >
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

      <MasteryReportCard />
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
        <div className="rounded-xl border border-line bg-card p-4 text-sm text-muted-foreground mt-6">
          <p className="font-medium text-foreground">No children linked to this email yet.</p>
          <p className="mt-1">
            If your child has signed up, make sure they entered <strong>this exact email address</strong> as
            their parent's email when registering. Once they do, they'll appear here.
          </p>
        </div>
      )}
      {!hintSeen && (q.data?.length ?? 0) > 0 && (
        <div className="mb-4 mt-6 flex items-start justify-between gap-3 rounded-xl border border-brand-200 bg-brand-50 p-3 text-sm">
          <span>Welcome! From here you can manage notifications, your subscription, Face ID sign-in, and your child's data.</span>
          <button type="button" className="font-semibold text-brand-700" onClick={() => { localStorage.setItem('parent-welcome-seen', '1'); setHintSeen(true); }}>Got it</button>
        </div>
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
      <DeleteAccountCard />
      <FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} audience="parent" />
    </main>
  );
}
