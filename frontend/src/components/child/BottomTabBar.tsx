import { NavLink } from 'react-router-dom';
import { Home, BookOpen, TrendingUp, BarChart3, Target, RefreshCw } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '@/lib/utils';

const TABS: { to: string; key: string; Icon: React.ElementType }[] = [
  { to: '/home', key: 'nav.home', Icon: Home },
  { to: '/lessons', key: 'nav.learn', Icon: BookOpen },
  { to: '/revise', key: 'nav.revise', Icon: RefreshCw },
  { to: '/progress', key: 'nav.progress', Icon: Target },
  { to: '/simulator', key: 'nav.simulator', Icon: TrendingUp },
  { to: '/stats', key: 'nav.stats', Icon: BarChart3 },
];

export function BottomTabBar() {
  const { t } = useTranslation('child');
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-20 border-t border-gray-200/70 bg-white shadow-[0_-4px_12px_rgba(0,0,0,0.05)] md:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      aria-label={t('nav.primaryMobile')}
    >
      <div className="flex h-16 items-center justify-around">
        {TABS.map(({ to, key, Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center gap-0.5 px-3 py-1 text-xs transition-colors min-h-[44px] min-w-[44px] justify-center',
                isActive ? 'text-brand-600 font-extrabold' : 'text-gray-400 font-medium',
              )
            }
          >
            <Icon className="h-5 w-5" />
            <span>{t(key)}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
