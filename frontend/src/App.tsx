import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import ConsentVerify from '@/pages/ConsentVerify';
import ParentLogin from '@/pages/ParentLogin';
import ParentAuthCallback from '@/pages/ParentAuthCallback';
import ParentDashboard from '@/pages/ParentDashboard';

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/parent" replace />} />
        <Route path="/consent/verify" element={<ConsentVerify />} />
        <Route path="/parent/login" element={<ParentLogin />} />
        <Route path="/parent/auth/callback" element={<ParentAuthCallback />} />
        <Route path="/parent" element={<ParentDashboard />} />
        <Route path="*" element={<div className="p-6">Not found</div>} />
      </Routes>
      <Toaster />
    </>
  );
}
