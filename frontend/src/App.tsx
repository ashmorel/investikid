import { lazy, Suspense } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/toaster';
import { Shell } from '@/components/child/Shell';
import { BiometricGate } from '@/components/auth/BiometricGate';
import { LiveRegion } from '@/components/a11y/LiveRegion';
import Login from '@/pages/child/Login';
import Signup from '@/pages/child/Signup';
import PendingConsent from '@/pages/child/PendingConsent';
import Home from '@/pages/child/Home';
const Shop = lazy(() => import('@/pages/child/Shop'));
const ReviseSession = lazy(() => import('@/pages/child/ReviseSession'));
import Lessons from '@/pages/child/Lessons';
const Module = lazy(() => import('@/pages/child/Module'));
import Level from '@/pages/child/Level';
const Lesson = lazy(() => import('@/pages/child/Lesson'));
// Chart-heavy routes are lazy-loaded so recharts/chart code stays out of the
// child-facing main bundle (a kid on /home never pays for it).
const Simulator = lazy(() => import('@/pages/child/Simulator'));
const Market = lazy(() => import('@/pages/child/Market'));
import { Markets } from '@/pages/child/Markets';
const Stock = lazy(() => import('@/pages/child/Stock'));
const Stats = lazy(() => import('@/pages/child/Stats'));
import Revise from '@/pages/child/Revise';
import StrengthsGaps from '@/pages/child/StrengthsGaps';
import Coach from '@/pages/child/Coach';
import Arcade from '@/pages/child/Arcade';
import QuizRush from '@/pages/child/games/QuizRush';
import MoneyWord from '@/pages/child/games/MoneyWord';
import Downloaded from '@/pages/child/Downloaded';
import ConsentVerify from '@/pages/ConsentVerify';
import ForgotPassword from '@/pages/ForgotPassword';
import Privacy from '@/pages/Privacy';
import DeleteAccount from '@/pages/DeleteAccount';
const Try = lazy(() => import('@/pages/Try'));
const LearningEvidence = lazy(() => import('@/pages/LearningEvidence'));
const OnboardingDiagnostic = lazy(() => import('@/pages/child/OnboardingDiagnostic'));
import ResetPassword from '@/pages/ResetPassword';
import VerifyEmail from '@/pages/VerifyEmail';
import ParentLogin from '@/pages/ParentLogin';
import ParentAuthCallback from '@/pages/ParentAuthCallback';
const ParentDashboard = lazy(() => import('@/pages/ParentDashboard'));
// Admin tree is lazy-loaded so it stays out of the child-facing main bundle.
const AdminLayout = lazy(() => import('@/components/admin/AdminLayout'));
const AdminDashboard = lazy(() => import('@/components/admin/AdminDashboard'));
const ModuleList = lazy(() => import('@/components/admin/ModuleList'));
const ModuleForm = lazy(() => import('@/components/admin/ModuleForm'));
const LevelList = lazy(() => import('@/components/admin/LevelList'));
const LevelLessonList = lazy(() => import('@/components/admin/LevelLessonList'));
const BadgeList = lazy(() => import('@/components/admin/BadgeList'));
const BadgeForm = lazy(() => import('@/components/admin/BadgeForm'));
const ChallengeList = lazy(() => import('@/components/admin/ChallengeList'));
const ChallengeForm = lazy(() => import('@/components/admin/ChallengeForm'));
const FeedbackList = lazy(() => import('@/components/admin/FeedbackList'));
const VideoHealthList = lazy(() => import('@/components/admin/VideoHealthList'));
const VideoCuration = lazy(() => import('@/components/admin/VideoCuration'));
const AdminSettings = lazy(() => import('@/components/admin/AdminSettings'));
const AdminAnalytics = lazy(() => import('@/components/admin/AdminAnalytics'));
const MarketContent = lazy(() => import('@/components/admin/MarketContent'));
const ArcadeWordBank = lazy(() => import('@/components/admin/ArcadeWordBank'));
const CollectablesAdmin = lazy(() => import('@/components/admin/CollectablesAdmin'));
const ConceptsAdmin = lazy(() => import('@/components/admin/ConceptsAdmin'));
const DiagnosticItemsAdmin = lazy(() => import('@/components/admin/DiagnosticItemsAdmin'));

function RootRedirect() {
  // Redirect / to /home; if unauthed, /home's Shell will redirect to /login.
  return <Navigate to="/home" replace />;
}

function OnboardingDiagnosticRoute() {
  const nav = useNavigate();
  const queryClient = useQueryClient();
  function handleComplete() {
    // Invalidate the evidence cache so the Shell gate stops redirecting.
    void queryClient.invalidateQueries({ queryKey: ['diagnostic', 'evidence'] });
    nav('/home', { replace: true });
  }
  return (
    <Suspense fallback={null}>
      <OnboardingDiagnostic onComplete={handleComplete} />
    </Suspense>
  );
}

function ProgressCheckRoute() {
  const nav = useNavigate();
  const queryClient = useQueryClient();
  function handleComplete() {
    // Invalidate both the recheck status (milestone consumed) and evidence.
    void queryClient.invalidateQueries({ queryKey: ['diagnostic', 'recheck'] });
    void queryClient.invalidateQueries({ queryKey: ['diagnostic', 'evidence'] });
    nav('/home', { replace: true });
  }
  return (
    <Suspense fallback={null}>
      <OnboardingDiagnostic kind="progress" onComplete={handleComplete} />
    </Suspense>
  );
}

export default function App() {
  return (
    <LiveRegion>
      <BiometricGate>
      <Routes>
        <Route path="/" element={<RootRedirect />} />

        {/* Public child routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/delete-account" element={<DeleteAccount />} />
        <Route path="/try" element={<Suspense fallback={null}><Try /></Suspense>} />
        <Route path="/how-we-measure" element={<Suspense fallback={null}><LearningEvidence /></Suspense>} />
        <Route path="/pending-consent" element={<PendingConsent />} />
        <Route path="/onboarding/diagnostic" element={<OnboardingDiagnosticRoute />} />
        <Route path="/progress-check" element={<ProgressCheckRoute />} />
        <Route path="/forgot-password" element={<ForgotPassword />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/verify-email" element={<VerifyEmail />} />

        {/* Authed child routes inside Shell */}
        <Route element={<Shell />}>
          <Route path="/home" element={<Home />} />
          <Route path="/shop" element={<Shop />} />
          <Route path="/lessons" element={<Lessons />} />
          <Route path="/lessons/:moduleId" element={<Suspense fallback={null}><Module /></Suspense>} />
          <Route path="/lessons/:moduleId/:levelId" element={<Level />} />
          <Route path="/lessons/:moduleId/:levelId/:lessonId" element={<Suspense fallback={null}><Lesson /></Suspense>} />
          <Route path="/simulator" element={<Suspense fallback={null}><Simulator /></Suspense>} />
          <Route path="/simulator/market" element={<Suspense fallback={null}><Market /></Suspense>} />
          <Route path="/simulator/stock/:exchange/:ticker" element={<Suspense fallback={null}><Stock /></Suspense>} />
          <Route path="/markets" element={<Markets />} />
          <Route path="/stats" element={<Suspense fallback={null}><Stats /></Suspense>} />
          <Route path="/progress" element={<StrengthsGaps />} />
          <Route path="/revise" element={<Revise />} />
          <Route path="/revise/session" element={<Suspense fallback={null}><ReviseSession /></Suspense>} />
          <Route path="/coach" element={<Coach />} />
          <Route path="/arcade" element={<Arcade />} />
          <Route path="/arcade/quiz-rush" element={<QuizRush />} />
          <Route path="/arcade/moneyword" element={<MoneyWord />} />
          <Route path="/downloaded" element={<Downloaded />} />
        </Route>

        {/* Existing parent + consent routes (untouched) */}
        <Route path="/consent/verify" element={<ConsentVerify />} />
        <Route path="/parent/login" element={<ParentLogin />} />
        <Route path="/parent/auth/callback" element={<ParentAuthCallback />} />
        <Route path="/parent" element={<Suspense fallback={null}><ParentDashboard /></Suspense>} />

        {/* Admin routes */}
        <Route
          path="/admin"
          element={
            <Suspense
              fallback={
                <div className="flex min-h-screen items-center justify-center bg-background">
                  <span className="text-muted-foreground">Loading…</span>
                </div>
              }
            >
              <AdminLayout />
            </Suspense>
          }
        >
          <Route index element={<AdminDashboard />} />
          <Route path="modules" element={<ModuleList />} />
          <Route path="modules/new" element={<ModuleForm />} />
          <Route path="modules/:moduleId" element={<ModuleForm />} />
          <Route path="modules/:moduleId/levels" element={<LevelList />} />
          <Route path="modules/:moduleId/levels/:levelId/lessons" element={<LevelLessonList />} />
          <Route path="badges" element={<BadgeList />} />
          <Route path="badges/new" element={<BadgeForm />} />
          <Route path="badges/:badgeId" element={<BadgeForm />} />
          <Route path="challenges" element={<ChallengeList />} />
          <Route path="challenges/new" element={<ChallengeForm />} />
          <Route path="challenges/:challengeId" element={<ChallengeForm />} />
          <Route path="feedback" element={<FeedbackList />} />
          <Route path="video-health" element={<VideoHealthList />} />
          <Route path="video-curation" element={<VideoCuration />} />
          <Route path="market-content" element={<MarketContent />} />
          <Route path="arcade-words" element={<ArcadeWordBank />} />
          <Route path="collectables" element={<CollectablesAdmin />} />
          <Route path="concepts" element={<ConceptsAdmin />} />
          <Route path="diagnostic-items" element={<DiagnosticItemsAdmin />} />
          <Route path="settings" element={<AdminSettings />} />
          <Route path="analytics" element={<AdminAnalytics />} />
        </Route>

        <Route path="*" element={<div className="p-6">Not found</div>} />
      </Routes>
      </BiometricGate>
      <Toaster />
    </LiveRegion>
  );
}
