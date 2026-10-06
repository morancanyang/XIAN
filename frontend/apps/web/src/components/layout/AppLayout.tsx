import { NavLink, Outlet } from 'react-router-dom';
import { Badge, Kbd } from '@xian/ui';
import { cn } from '../../lib/utils/cn';
import { useSessionStore } from '../../store/sessionStore';
import { useEventStore } from '../../store/eventStore';
import { AlertHost } from '@xian/ui';
import { ToastProvider } from './ToastHost';
import { LlmStatusChip } from '../ui/LlmStatusChip';

const NAV = [
  { to: '/dashboard', label: '驾驶舱', hint: 'Dashboard' },
  { to: '/scenarios', label: '靶场场景', hint: 'Scenarios' },
  { to: '/agents', label: 'Agent 资产', hint: 'Assets' },
  { to: '/campaigns', label: '模式一', hint: '战役' },
  { to: '/console', label: '模式二', hint: '自由攻击' },
  { to: '/levels', label: '关卡', hint: '十关挑战' },
  { to: '/matrix', label: '攻击矩阵', hint: 'Matrix' },
  { to: '/reports', label: '报告中心', hint: 'Reports' },
  { to: '/admin', label: '管理', hint: 'Admin' },
  { to: '/profile', label: '个人中心', hint: 'Profile' }
];

/** 全局布局：左侧导航 + 顶栏（技术方案 8.3）。 */
export function AppLayout() {
  const connection = useEventStore((s) => s.connection);
  const alert = useEventStore((s) => s.alert);
  const pushAlert = useEventStore((s) => s.pushAlert);
  const env = import.meta.env.VITE_APP_ENV ?? 'dev';

  return (
    <ToastProvider>
      <div className="flex h-full min-h-screen">
        <aside className="sticky top-0 flex h-screen w-60 shrink-0 flex-col border-r border-border bg-elevated/60 backdrop-blur">
          <div className="flex items-center gap-2 px-4 py-4">
            <span className="flex h-8 w-8 items-center justify-center rounded-control bg-blue-team font-mono text-sm font-bold text-white">
              X
            </span>
            <div>
              <p className="text-sm font-semibold leading-tight">XIAN</p>
              <p className="text-[10px] text-content-faint">红蓝对抗平台</p>
            </div>
          </div>
          <nav className="flex-1 space-y-0.5 overflow-y-auto px-2 pb-4 xian-scrollbar">
            {NAV.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  cn(
                    'flex items-center justify-between rounded-control px-3 py-2 text-sm transition-colors duration-fast',
                    isActive ? 'bg-blue-team/15 text-blue-team' : 'text-content-muted hover:bg-white/5 hover:text-content'
                  )
                }
              >
                <span>{item.label}</span>
                <span className="text-[10px] text-content-faint">{item.hint}</span>
              </NavLink>
            ))}
          </nav>
          <div className="border-t border-border px-3 py-3 text-[10px] text-content-faint">
            <p>技术方案 v1.0</p>
            <p>PRD 3.1 ~ 3.9 全覆盖</p>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-sticky flex items-center gap-3 border-b border-border bg-base/85 px-5 py-2.5 backdrop-blur">
            <Badge tone={env === 'prod' ? 'danger' : 'coach'}>{env === 'prod' ? '生产环境' : '开发环境'}</Badge>
            <span className="text-xs text-content-faint">租户 {shortTenant(useSessionStore.getState().tenantId)}</span>
            <div className="ml-auto flex items-center gap-3 text-xs text-content-muted">
              <span className="flex items-center gap-1.5">
                <span
                  className={cn(
                    'h-1.5 w-1.5 rounded-full',
                    connection === 'open' ? 'bg-success' : connection === 'error' ? 'bg-danger' : 'bg-coach'
                  )}
                />
                {connection === 'open' ? '实时已连接' : connection === 'connecting' ? '连接中' : '未连接'}
              </span>
              <LlmStatusChip className="hidden sm:flex" />
              <span className="hidden items-center gap-1 md:flex">
                命令面板 <Kbd>Ctrl</Kbd>+<Kbd>K</Kbd>
              </span>
              <NavLink to="/profile" className="hover:text-content">
                个人中心
              </NavLink>
            </div>
          </header>

          {alert ? <AlertHost alert={alert} onDismiss={() => pushAlert(null)} className="m-4 mb-0" /> : null}

          <main className="min-w-0 flex-1 p-5">
            <Outlet />
          </main>
        </div>
      </div>
    </ToastProvider>
  );
}

function shortTenant(id: string): string {
  return id.length > 8 ? `${id.slice(0, 8)}…` : id;
}
