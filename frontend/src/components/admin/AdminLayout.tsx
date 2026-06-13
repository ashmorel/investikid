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
    // Stack the nav on top on mobile, sidebar beside content on md+.
    <div className="flex min-h-screen flex-col bg-background md:flex-row">
      <AdminSidebar />
      {/* min-w-0 lets this flex child shrink below its content's intrinsic width;
          overflow-x-auto keeps wide tables scrolling inside the page instead of
          spilling off the right edge on narrow screens. */}
      <main className="min-w-0 flex-1 overflow-x-auto p-4 md:p-6">
        <Outlet />
      </main>
    </div>
  );
}
