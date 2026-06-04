import { Navigate, Outlet } from 'react-router-dom';
import { useChildSession } from '@/hooks/useChildSession';
import AdminSidebar from './AdminSidebar';

export default function AdminLayout() {
  const { data: session, isLoading } = useChildSession();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <span className="text-muted-foreground">Loading…</span>
      </div>
    );
  }

  if (!session || !session.is_admin) {
    return <Navigate to="/home" replace />;
  }

  return (
    <div className="flex min-h-screen bg-background">
      <AdminSidebar />
      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
