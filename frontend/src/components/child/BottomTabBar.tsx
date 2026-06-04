import { NavLink } from 'react-router-dom';
import { Home, BookOpen, TrendingUp, BarChart3, Target } from 'lucide-react';
import { cn } from '@/lib/utils';

const TABS = [
  { to: '/home', label: 'Home', Icon: Home },
  { to: '/lessons', label: 'Quests', Icon: BookOpen },
  { to: '/progress', label: 'Progress', Icon: Target },
  { to: '/simulator', label: 'Simulator', Icon: TrendingUp },
  { to: '/stats', label: 'Stats', Icon: BarChart3 },
] as const;

export function BottomTabBar() {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-20 border-t border-gray-200/70 bg-white shadow-[0_-4px_12px_rgba(0,0,0,0.05)] md:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
      aria-label="Primary mobile"
    >
      <div className="flex h-16 items-center justify-around">
        {TABS.map(({ to, label, Icon }) => (
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
            <span>{label}</span>
          </NavLink>
        ))}
      </div>
    </nav>
  );
}
