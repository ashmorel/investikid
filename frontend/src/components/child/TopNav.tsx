import { Link, NavLink } from 'react-router-dom';
import { ProfileMenu } from './ProfileMenu';
import { cn } from '@/lib/utils';

const NAV_LINKS = [
  { to: '/home', label: 'Home' },
  { to: '/lessons', label: 'Quests' },
  { to: '/simulator', label: 'Simulator' },
  { to: '/stats', label: 'Stats' },
] as const;

export function TopNav({ username }: { username: string }) {
  return (
    <header className="sticky top-0 z-10 border-b border-amber-200 bg-white/95 backdrop-blur" style={{ paddingTop: 'var(--safe-top)' }}>
      <div className="mx-auto flex h-14 max-w-5xl items-center gap-2 px-4">
        <Link to="/home" className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-amber-400 to-orange-500 text-center text-sm font-extrabold text-white">IE</span>
          <span className="text-lg font-extrabold text-gray-900">Invest-Ed</span>
        </Link>

        <nav className="ml-6 hidden items-center gap-1 md:flex" aria-label="Primary">
          {NAV_LINKS.map(({ to, label }) => (
            <NavLink key={to} to={to}
              className={({ isActive }) => cn(
                'px-3 py-1.5 text-sm font-semibold rounded-lg transition-colors',
                isActive
                  ? 'text-amber-600 bg-amber-50 border-b-2 border-amber-400'
                  : 'text-gray-600 hover:text-amber-600 hover:bg-amber-50',
              )}>{label}</NavLink>
          ))}
        </nav>

        <div className="ml-auto">
          <ProfileMenu username={username} />
        </div>
      </div>
    </header>
  );
}
