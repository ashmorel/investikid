import { Outlet, useLocation } from 'react-router-dom';
import { AnimatePresence, motion, useReducedMotion } from 'framer-motion';
import { useChildSession } from '@/hooks/useChildSession';
import { useChildAuthGuard } from '@/hooks/useChildAuthGuard';
import { VerifyEmailBanner } from '@/components/VerifyEmailBanner';
import { TopNav } from './TopNav';
import { TierBadge } from './TierBadge';
import { BottomTabBar } from './BottomTabBar';
import { SkipLink } from '@/components/a11y/SkipLink';
import { useRouteFocus } from '@/components/a11y/useRouteFocus';

export function Shell() {
  const session = useChildSession();
  useChildAuthGuard(session.error);
  const location = useLocation();
  const prefersReducedMotion = useReducedMotion();
  useRouteFocus();

  if (session.isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-amber-50 to-orange-50">
        <header className="h-14 border-b border-amber-200" aria-busy="true" />
        <p className="mx-auto mt-6 max-w-2xl px-4 text-sm text-muted-foreground">Loading…</p>
      </div>
    );
  }

  if (!session.data) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 to-orange-50">
      <SkipLink />
      <TopNav username={session.data.username} />
      <div className="mx-auto flex max-w-5xl items-center px-4 pt-2">
        <TierBadge premium={session.data.is_premium} />
      </div>
      <VerifyEmailBanner profile={session.data} />
      <AnimatePresence mode="wait">
        <motion.main
          key={location.pathname}
          id="main"
          tabIndex={-1}
          className="pb-20 md:pb-0 outline-none"
          initial={prefersReducedMotion ? false : { opacity: 0, y: 8 }}
          animate={prefersReducedMotion ? undefined : { opacity: 1, y: 0 }}
          exit={prefersReducedMotion ? undefined : { opacity: 0, y: -8 }}
          transition={{ duration: prefersReducedMotion ? 0 : 0.15 }}
        >
          <Outlet />
        </motion.main>
      </AnimatePresence>
      <BottomTabBar />
    </div>
  );
}
