import { Suspense, lazy, useEffect } from 'react';
import { Route, Routes, useLocation } from 'react-router-dom';
import {
  TooltipProvider,
  Threads,
  GlobalLoading,
  useReducedMotion,
  ErrorBoundary
} from '@xian/ui';
import { useSessionStore } from './store/sessionStore';
import { AppLayout } from './components/layout/AppLayout';
import { ToastProvider } from './components/layout/ToastHost';
import { CommandPalette } from './components/layout/CommandPalette';
import { NotFound } from './pages/NotFound';

/* 路由级 React.lazy：重图路由不进入首屏包（技术方案 8.1 性能预算） */
const HomePage = lazy(() => import('./pages/home/HomePage'));
const LoginPage = lazy(() => import('./pages/auth/LoginPage'));
const AgentsPage = lazy(() => import('./pages/agents/AgentsPage'));
const AgentDetailPage = lazy(() => import('./pages/agents/AgentDetailPage'));
const ScenarioMarketPage = lazy(() => import('./pages/scenarios/ScenarioMarketPage'));
const ScenarioDetailPage = lazy(() => import('./pages/scenarios/ScenarioDetailPage'));
const CampaignsPage = lazy(() => import('./pages/mode1/CampaignsPage'));
const CampaignCreatePage = lazy(() => import('./pages/mode1/CampaignCreatePage'));
const CampaignLivePage = lazy(() => import('./pages/mode1/CampaignLivePage'));
const AttackConsolePage = lazy(() => import('./pages/mode2/AttackConsolePage'));
const LevelMapPage = lazy(() => import('./pages/mode2/LevelMapPage'));
const MatrixPage = lazy(() => import('./pages/matrix/MatrixPage'));
const ReportsPage = lazy(() => import('./pages/reports/ReportsPage'));
const ReportViewPage = lazy(() => import('./pages/reports/ReportViewPage'));
const AdminPage = lazy(() => import('./pages/admin/AdminPage'));
const ProfilePage = lazy(() => import('./pages/profile/ProfilePage'));

export function App() {
  const reducedMotion = useSessionStore((s) => s.reducedMotion);
  /* 与 @xian/ui useReducedMotion 同源（localStorage + 系统偏好），保证 CSS 降级选择器能命中 */
  const uiReducedMotion = useReducedMotion();
  const { pathname } = useLocation();
  /* / 与 /login 是登录页；/profile 自带柔化氛围层：均跳过全局线条背景，避免硬线叠加 */
  const skipGlobalBackdrop = pathname === '/' || pathname === '/login' || pathname === '/profile';

  useEffect(() => {
    document.documentElement.dataset.reducedMotion = reducedMotion || uiReducedMotion ? 'true' : 'false';
  }, [reducedMotion, uiReducedMotion]);

  return (
    <ToastProvider>
      <TooltipProvider delayDuration={200}>
        {/* 全局默认背景：根布局最外层、所有页面之下（技术方案 8.7.1）。
            登录页自带红蓝擂台背景，此处跳过，避免隐藏的 WebGL 循环空跑 GPU。 */}
        <ErrorBoundary label="背景加载异常">
          {skipGlobalBackdrop ? null : <Threads />}
        </ErrorBoundary>
        <ErrorBoundary label="页面加载异常">
        <Suspense fallback={<GlobalLoading visible label="页面加载中" />}>
          <Routes>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<HomePage />} />
              <Route path="/agents" element={<AgentsPage />} />
              <Route path="/agents/:agentId" element={<AgentDetailPage />} />
              <Route path="/scenarios" element={<ScenarioMarketPage />} />
              <Route path="/scenarios/:code" element={<ScenarioDetailPage />} />
              <Route path="/campaigns" element={<CampaignsPage />} />
              <Route path="/campaigns/new" element={<CampaignCreatePage />} />
              <Route path="/campaigns/:campaignId" element={<CampaignLivePage />} />
              <Route path="/console" element={<AttackConsolePage />} />
              <Route path="/console/:sessionId" element={<AttackConsolePage />} />
              <Route path="/levels" element={<LevelMapPage />} />
              <Route path="/matrix" element={<MatrixPage />} />
              <Route path="/reports" element={<ReportsPage />} />
              <Route path="/reports/:reportId" element={<ReportViewPage />} />
              <Route path="/admin" element={<AdminPage />} />
              <Route path="/profile" element={<ProfilePage />} />
            </Route>
            <Route path="/" element={<LoginPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
        </ErrorBoundary>
      </TooltipProvider>
      <CommandPalette />
    </ToastProvider>
  );
}






