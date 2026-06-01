import { NavLink } from 'react-router-dom';

const NAV_ITEMS = [
  { to: '/admin', label: 'Dashboard', icon: '📊', end: true },
  { to: '/admin/modules', label: 'Modules', icon: '📖', end: false },
  { to: '/admin/badges', label: 'Badges', icon: '🏆', end: false },
  { to: '/admin/challenges', label: 'Challenges', icon: '⚡', end: false },
  { to: '/admin/feedback', label: 'Feedback', icon: '💬', end: false },
  { to: '/admin/settings', label: 'Settings', icon: '⚙️', end: false },
];

export default function AdminSidebar() {
  return (
    <aside className="flex w-52 flex-col border-r border-slate-700 bg-slate-900 p-4">
      <div className="mb-6 text-lg font-bold text-slate-50">📚 Invest-Ed Admin</div>
      <nav className="flex flex-col gap-1" aria-label="Admin navigation">
        {NAV_ITEMS.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              `rounded-md px-3 py-2 text-sm ${
                isActive ? 'bg-blue-600 text-white' : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`
            }
          >
            {item.icon} {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="mt-auto border-t border-slate-700 pt-4">
        <a href="/" className="text-sm text-slate-500 hover:text-slate-300">← Back to App</a>
      </div>
    </aside>
  );
}
