import { NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { BackToAppButton } from '@/components/BackToAppButton';

const NAV_ITEMS = [
  { to: '/admin', tKey: 'sidebar.items.dashboard', icon: '📊', end: true },
  { to: '/admin/modules', tKey: 'sidebar.items.modules', icon: '📖', end: false },
  { to: '/admin/badges', tKey: 'sidebar.items.badges', icon: '🏆', end: false },
  { to: '/admin/challenges', tKey: 'sidebar.items.challenges', icon: '⚡', end: false },
  { to: '/admin/feedback', tKey: 'sidebar.items.feedback', icon: '💬', end: false },
  { to: '/admin/video-health', tKey: 'sidebar.items.videoHealth', icon: '🎬', end: false },
  { to: '/admin/video-curation', tKey: 'sidebar.items.videoCuration', icon: '🎞️', end: false },
  { to: '/admin/market-content', tKey: 'sidebar.items.marketContent', icon: '🌍', end: false },
  { to: '/admin/arcade-words', tKey: 'sidebar.items.arcadeWordBank', icon: '🃏', end: false },
  { to: '/admin/analytics', tKey: 'sidebar.items.analytics', icon: '📈', end: false },
  { to: '/admin/settings', tKey: 'sidebar.items.settings', icon: '⚙️', end: false },
];

export default function AdminSidebar() {
  const { t } = useTranslation('admin');
  return (
    // Mobile: a full-width top bar with a horizontally scrollable nav row.
    // md+: a fixed-width vertical sidebar beside the content.
    // paddingTop carries the safe-area inset so the title clears the iOS
    // status bar / notch when this is the top bar (native app); --safe-top is
    // 0 on the desktop sidebar and in browser tabs.
    <aside
      className="flex w-full shrink-0 flex-col border-b border-line bg-card px-3 pb-3 md:w-52 md:border-b-0 md:border-r md:px-4 md:pb-4"
      style={{ paddingTop: 'calc(var(--safe-top) + 0.75rem)' }}
    >
      <div className="mb-3 md:mb-6">
        <div className="text-base font-extrabold text-ink md:text-lg">📚 {t('sidebar.title')}</div>
        <BackToAppButton className="mt-1 -ml-1" />
      </div>
      <nav
        className="flex flex-row gap-1 overflow-x-auto pb-1 md:flex-col md:overflow-x-visible md:pb-0"
        aria-label={t('sidebar.nav')}
      >
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `shrink-0 whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium ${
                isActive
                  ? 'bg-brand-600 text-white'
                  : 'text-muted-foreground hover:bg-brand-50 hover:text-ink'
              }`
            }
          >
            {item.icon} {t(item.tKey)}
          </NavLink>
        ))}
      </nav>
    </aside>
  );
}
