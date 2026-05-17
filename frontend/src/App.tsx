import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { Shell } from '@/components/child/Shell';
import Login from '@/pages/child/Login';
import Signup from '@/pages/child/Signup';
import PendingConsent from '@/pages/child/PendingConsent';
import Home from '@/pages/child/Home';
import Lessons from '@/pages/child/Lessons';
import Module from '@/pages/child/Module';
import Lesson from '@/pages/child/Lesson';
import Simulator from '@/pages/child/Simulator';
import Market from '@/pages/child/Market';
import Stock from '@/pages/child/Stock';
import Stats from '@/pages/child/Stats';
import ConsentVerify from '@/pages/ConsentVerify';
import ForgotPassword from '@/pages/ForgotPassword';
import Privacy from '@/pages/Privacy';
import ResetPassword from '@/pages/ResetPassword';
import VerifyEmail from '@/pages/VerifyEmail';
import ParentLogin from '@/pages/ParentLogin';
import ParentAuthCallback from '@/pages/ParentAuthCallback';
import ParentDashboard from '@/pages/ParentDashboard';

function RootRedirect() {
  // Redirect / to /home; if unauthed, /home's Shell will redirect to /login.
  return <Navigate to="/home" replace />;
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<RootRedirect />} />

        {/* Public child routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/pending-consent" element={<PendingConsent />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />

        {/* Authed child routes inside Shell */}
        <Route element={<Shell />}>
          <Route path="/home" element={<Home />} />
          <Route path="/lessons" element={<Lessons />} />
          <Route path="/lessons/:moduleId" element={<Module />} />
          <Route path="/lessons/:moduleId/:lessonId" element={<Lesson />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/simulator/market" element={<Market />} />
          <Route path="/simulator/stock/:exchange/:ticker" element={<Stock />} />
          <Route path="/stats" element={<Stats />} />
        </Route>

        {/* Existing parent + consent routes (untouched) */}
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
