import { Link, NavLink } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { ProfileMenu } from './ProfileMenu';
import { cn } from '@/lib/utils';

const NAV_LINK_KEYS = [
  { to: '/home', key: 'nav.home' },
  { to: '/lessons', key: 'nav.learn' },
  { to: '/progress', key: 'nav.progress' },
  { to: '/simulator', key: 'nav.simulator' },
  { to: '/stats', key: 'nav.stats' },
] as const;

export function TopNav({ username }: { username: string }) {
  const { t } = useTranslation('child');
  return (
    <header className="sticky top-0 z-10 border-b border-brand-200 bg-white/95 backdrop-blur" style={{ paddingTop: 'var(--safe-top)' }}>
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-4">
        <Link to="/home" className="flex items-center gap-2">
          <img src="/icons/icon-192.png" alt="" width={32} height={32} className="h-8 w-8 rounded-full" />
          <span className="text-lg font-extrabold text-gray-900">{t('topNav.homeLink')}</span>
        </Link>

        <nav className="ml-6 hidden items-center gap-1 md:flex" aria-label={t('nav.primary')}>
          {NAV_LINK_KEYS.map(({ to, key }) => (
            <NavLink key={to} to={to}
              className={({ isActive }) => cn(
                'px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors',
                isActive
                  ? 'text-brand-600 bg-brand-100 border-b-2 border-brand-400'
                  : 'text-gray-600 hover:text-brand-600 hover:bg-brand-50',
              )}>{t(key)}</NavLink>
          ))}
        </nav>

        <div className="ml-auto">
          <ProfileMenu username={username} />
        </div>
      </div>
    </header>
  );
}
