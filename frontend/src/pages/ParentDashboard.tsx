import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { parentApi, type Child } from '@/api/parent';
import { authApi } from '@/api/auth';
import { useParentAuthGuard } from '@/hooks/useParentAuthGuard';
import { ChildCard } from '@/components/ChildCard';
import { SubscriptionCard } from '@/components/SubscriptionCard';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import { Menu } from 'lucide-react';
import { ErrorBanner } from '@/components/ErrorBanner';
import { useToast } from '@/hooks/use-toast';
import { FeedbackDialog } from '@/components/child/FeedbackDialog';
import { SignInMethods } from '@/components/parent/SignInMethods';
import { LanguageSwitcher } from '@/components/settings/LanguageSwitcher';
import { GroupsCard } from '@/components/parent/GroupsCard';
import { NotificationPreferencesCard } from '@/components/parent/NotificationPreferencesCard';
import { PremiumRequestsCard } from '@/components/parent/PremiumRequestsCard';
import { MasteryReportCard } from '@/components/parent/MasteryReportCard';
import { PremiumValueCard } from '@/components/parent/PremiumValueCard';
import { DeleteAccountCard } from '@/components/parent/DeleteAccountCard';
import { Penny } from '@/components/child/ui/Penny';

export default function ParentDashboard() {
  const { t } = useTranslation('parent');
  const navigate = useNavigate();
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['children'], queryFn: parentApi.listChildren });
  useParentAuthGuard(q.error);

  // A bridge user (a verified app user who is also a parent) reaches the parent
  // area from the child app and keeps their app session. Standalone magic-link
  // parents have no app session, so /me 401s — expected; no redirect here.
  const me = useQuery({ queryKey: ['me'], queryFn: () => authApi.me(), retry: false, staleTime: 5 * 60_000 });
  const hasAppSession = Boolean(me.data);

  const logout = useMutation({
    // Clear BOTH the parent session and any app session so "Log out" actually
    // signs the bridge user out (not just out of the parent view), then send
    // them to the normal sign-in screen.
    mutationFn: async () => {
      await parentApi.logout().catch(() => {});
      await authApi.logout().catch(() => {});
    },
    onSettled: () => {
      qc.removeQueries({ queryKey: ['children'] });
      qc.removeQueries({ queryKey: ['me'] });
      navigate('/login', { replace: true });
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
        title: t('dashboard.checkoutToast.title'),
        description: t('dashboard.checkoutToast.description'),
      });
      searchParams.delete('checkout');
      setSearchParams(searchParams, { replace: true });
    } else if (checkoutResult === 'canceled') {
      searchParams.delete('checkout');
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams, toast, t]);

  return (
    <main className="mx-auto max-w-2xl px-4 py-4 sm:px-6 sm:py-6">
      <header
        className="sticky top-0 z-10 -mx-4 -mt-4 mb-4 flex items-center justify-between border-b border-brand-200 bg-white/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:-mt-6 sm:px-6"
        style={{ paddingTop: 'calc(env(safe-area-inset-top, 0px) + 0.75rem)' }}
      >
        <div className="flex items-center gap-2">
          <Link to="/parent" className="flex items-center gap-2" aria-label={t('dashboard.homeAriaLabel')}>
            <Penny size={32} mood="happy" />
            {/* eslint-disable-next-line i18next/no-literal-string -- brand name, not translatable */}
            <span className="text-lg font-extrabold tracking-tight text-ink sm:text-xl">InvestiKid</span>
          </Link>
          <h1 className="sr-only">{t('dashboard.title')}</h1>
        </div>
        <div className="flex items-center gap-1">
          {hasAppSession && (
            <button
              type="button"
              onClick={() => navigate('/home')}
              className="whitespace-nowrap rounded-md px-2 py-1.5 text-sm font-medium text-muted-foreground hover:text-ink"
            >
              {t('dashboard.backToApp')}
            </button>
          )}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" aria-label={t('dashboard.menuAriaLabel')}>
                <Menu className="h-5 w-5" aria-hidden="true" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onSelect={() => setFeedbackOpen(true)}>
                {t('dashboard.sendFeedback')}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onSelect={() => logout.mutate()}
                disabled={logout.isPending}
              >
                {t('dashboard.logOut')}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
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

      {q.isLoading && <p className="mt-6 text-sm text-muted-foreground">{t('dashboard.loading')}</p>}
      {q.isError && (
        <ErrorBanner
          className="mt-6"
          title={t('dashboard.childrenLoadError.title')}
          message={t('dashboard.childrenLoadError.message')}
        />
      )}
      {q.data && q.data.length === 0 && (
        <div className="rounded-xl border border-line bg-card p-4 text-sm text-muted-foreground mt-6">
          <p className="font-medium text-foreground">{t('dashboard.noChildrenLinked')}</p>
          <p className="mt-1">
            {t('dashboard.noChildrenLinkedHelp')}
          </p>
        </div>
      )}
      {!hintSeen && (q.data?.length ?? 0) > 0 && (
        <div className="mb-4 mt-6 flex items-start justify-between gap-3 rounded-xl border border-brand-200 bg-brand-50 p-3 text-sm">
          <span>{t('dashboard.welcome')}</span>
          <button type="button" className="font-semibold text-brand-700" onClick={() => { localStorage.setItem('parent-welcome-seen', '1'); setHintSeen(true); }}>{t('dashboard.welcomeDismiss')}</button>
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
      <section className="mt-6 rounded-xl border border-line bg-card p-4">
        <p className="mb-3 text-sm font-semibold text-muted-foreground">{t('dashboard.preferences')}</p>
        <LanguageSwitcher />
      </section>
      <DeleteAccountCard />
      <FeedbackDialog open={feedbackOpen} onOpenChange={setFeedbackOpen} audience="parent" />
    </main>
  );
}
