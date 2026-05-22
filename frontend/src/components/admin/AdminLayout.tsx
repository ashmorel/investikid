import { useState, useCallback, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { getAdminToken, clearAdminToken } from '@/lib/adminAuth';
import AdminLogin from './AdminLogin';
import AdminSidebar from './AdminSidebar';

export default function AdminLayout() {
  const [authed, setAuthed] = useState(() => !!getAdminToken());

  const handleAuthenticated = useCallback(() => setAuthed(true), []);

  // Listen for 401 errors to log out
  useEffect(() => {
    function on401(e: Event) {
      if (e instanceof CustomEvent && e.detail?.status === 401) {
        clearAdminToken();
        setAuthed(false);
      }
    }
    window.addEventListener('admin-auth-error', on401);
    return () => window.removeEventListener('admin-auth-error', on401);
  }, []);

  if (!authed) return <AdminLogin onAuthenticated={handleAuthenticated} />;

  return (
    <div className="flex min-h-screen bg-slate-950">
      <AdminSidebar />
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
