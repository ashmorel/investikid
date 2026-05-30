import { Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from '@/components/ui/toaster';
import { Shell } from '@/components/child/Shell';
import { LiveRegion } from '@/components/a11y/LiveRegion';
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
import StrengthsGaps from '@/pages/child/StrengthsGaps';
import Coach from '@/pages/child/Coach';
import ConsentVerify from '@/pages/ConsentVerify';
import ForgotPassword from '@/pages/ForgotPassword';
import Privacy from '@/pages/Privacy';
import ResetPassword from '@/pages/ResetPassword';
import VerifyEmail from '@/pages/VerifyEmail';
import ParentLogin from '@/pages/ParentLogin';
import ParentAuthCallback from '@/pages/ParentAuthCallback';
import ParentDashboard from '@/pages/ParentDashboard';
import AdminLayout from '@/components/admin/AdminLayout';
import AdminDashboard from '@/components/admin/AdminDashboard';
import ModuleList from '@/components/admin/ModuleList';
import ModuleForm from '@/components/admin/ModuleForm';
import BadgeList from '@/components/admin/BadgeList';
import BadgeForm from '@/components/admin/BadgeForm';
import ChallengeList from '@/components/admin/ChallengeList';
import ChallengeForm from '@/components/admin/ChallengeForm';
import FeedbackList from '@/components/admin/FeedbackList';

function RootRedirect() {
  // Redirect / to /home; if unauthed, /home's Shell will redirect to /login.
  return <Navigate to="/home" replace />;
}

export default function App() {
  return (
    <LiveRegion>
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
          <Route path="/progress" element={<StrengthsGaps />} />
          <Route path="/coach" element={<Coach />} />
        </Route>

        {/* Existing parent + consent routes (untouched) */}
        <Route path="/consent/verify" element={<ConsentVerify />} />
        <Route path="/parent/login" element={<ParentLogin />} />
        <Route path="/parent/auth/callback" element={<ParentAuthCallback />} />
        <Route path="/parent" element={<ParentDashboard />} />

        {/* Admin routes */}
        <Route path="/admin" element={<AdminLayout />}>
          <Route index element={<AdminDashboard />} />
          <Route path="modules" element={<ModuleList />} />
          <Route path="modules/new" element={<ModuleForm />} />
          <Route path="modules/:moduleId" element={<ModuleForm />} />
          <Route path="badges" element={<BadgeList />} />
          <Route path="badges/new" element={<BadgeForm />} />
          <Route path="badges/:badgeId" element={<BadgeForm />} />
          <Route path="challenges" element={<ChallengeList />} />
          <Route path="challenges/new" element={<ChallengeForm />} />
          <Route path="challenges/:challengeId" element={<ChallengeForm />} />
          <Route path="feedback" element={<FeedbackList />} />
        </Route>

        <Route path="*" element={<div className="p-6">Not found</div>} />
      </Routes>
      <Toaster />
    </LiveRegion>
  );
}
