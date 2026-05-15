import { NavLink } from 'react-router-dom';
import { Home, BookOpen, TrendingUp, BarChart3 } from 'lucide-react';
import { cn } from '@/lib/utils';

const TABS = [
  { to: '/home', label: 'Home', Icon: Home },
  { to: '/lessons', label: 'Quests', Icon: BookOpen },
  { to: '/simulator', label: 'Simulator', Icon: TrendingUp },
  { to: '/stats', label: 'Stats', Icon: BarChart3 },
] as const;

export function BottomTabBar() {
  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-20 border-t border-amber-200 bg-white/95 backdrop-blur md:hidden"
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
                'flex flex-col items-center gap-0.5 px-3 py-1 text-xs font-medium transition-colors',
                isActive ? 'text-amber-600' : 'text-gray-400',
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
