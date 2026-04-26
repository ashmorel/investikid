import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';

function Placeholder({ name }: { name: string }) {
  return <div className="p-6"><h1 className="text-2xl font-semibold">{name}</h1></div>;
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Navigate to="/parent" replace />} />
        <Route path="/consent/verify" element={<Placeholder name="ConsentVerify" />} />
        <Route path="/parent/login" element={<Placeholder name="ParentLogin" />} />
        <Route path="/parent/auth/callback" element={<Placeholder name="ParentAuthCallback" />} />
        <Route path="/parent" element={<Placeholder name="ParentDashboard" />} />
        <Route path="*" element={<div className="p-6">Not found</div>} />
      </Routes>
      <Toaster />
    </>
  );
}
