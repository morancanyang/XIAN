import { forwardRef, useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import type { MotionValue } from 'framer-motion';
import { motion, useMotionValue, useScroll, useSpring, useTransform } from 'framer-motion';
import { Button, Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, Field, Input, cn, useReducedMotion } from '@xian/ui';
import { useSessionStore } from '../../store/sessionStore';
import { ApiClientError, api } from '../../lib/api/client';
import { getBackendBase, normalizeBase, setBackendBase } from '../../lib/config/backend';
import type { Role } from '@xian/types';
import { useToast } from '../../components/layout/ToastHost';

/** 红蓝机器人对抗擂台主题图：底层背景与漂浮卡片共图（public/assets/arena.jpg）。 */
const ARENA_IMG = '/assets/arena.jpg';

/** 演示租户 / 用户：与全局 RequestContext 默认值保持一致（技术方案 5 store/）。 */
const DEMO_TENANT = '00000000-0000-0000-0000-000000000001';
const DEMO_USER_ID = '00000000-0000-0000-0000-0000000000a1';

const EASE: [number, number, number, number] = [0.16, 1, 0.3, 1];

/** 左上角两枚导航按钮。 */
const NAV_ITEMS = [
  { label: '产品', to: '/agents' },
  { label: '方案', to: '/scenarios' }
];

/** 顶部中央胶囊菜单展开项：控制台真实路由，点击即可进入对应驾驶舱。 */
const MENU_ITEMS = [
  { label: 'Agent 编排', hint: '红蓝 Agent 资产与编排', to: '/agents' },
  { label: '靶场场景', hint: '场景市场与模板库', to: '/scenarios' },
  { label: '攻击矩阵', hint: '类别 × 阶段热力网格', to: '/matrix' },
  { label: '报告中心', hint: '演练结论与复盘', to: '/reports' }
];

/** 演练角色：登录态写入 sessionStore，决定全局权限。 */
const ROLES: Array<{ value: Role; label: string; team?: 'red' | 'blue' }> = [
  { value: 'red', label: '红军', team: 'red' },
  { value: 'blue', label: '蓝军', team: 'blue' },
  { value: 'admin', label: '管理员' },
  { value: 'analyst', label: '分析师' }
];

/**
 * 自动填充同步：浏览器保存的账号密码会直接写入 DOM，而 React 受控 state 仍是空值，
 * 下一次重渲染就会把用户刚敲的字「顶掉」，表现为输入框怎么也打不了字。
 * 这里把 DOM 真实取值回灌 state：mount 时同步一次（填充常发生在弹窗出现的瞬间），
 * 再以原生 input 事件兜底，覆盖填充晚于挂载、或未触发 React onChange 的情况。
 */
function useAutofillSync(value: string, onChange: (next: string) => void) {
  const ref = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const el = ref.current;
    /* 未聚焦才回灌：聚焦状态下 el.value 就是用户正在敲的内容，不能拿它覆盖 state */
    if (el && document.activeElement !== el && el.value !== value) onChange(el.value);
  }, [value, onChange]);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    /* 仅在输入框未聚焦时回灌：用户自己输入时仍走 React onChange，避免重复 setState 与输入法冲突 */
    const onNativeInput = () => {
      if (document.activeElement !== el && el.value !== value) onChange(el.value);
    };
    el.addEventListener('input', onNativeInput);
    return () => el.removeEventListener('input', onNativeInput);
  }, [value, onChange]);
  return ref;
}

/**
 * 反自动填充输入框：注册表单专用。
 * Chrome 会把本站已保存的账号口令直接写进表单，受控组件的 state 感知不到这次写入，
 * 之后再渲染就会把用户刚敲的字顶掉（表现为"输入框打不了字"）。
 * 常态 readOnly 让浏览器放弃填充，获焦瞬间解除，正常输入不受影响。
 */
const RegisterInput = forwardRef<HTMLInputElement, React.ComponentProps<typeof Input>>(
  function RegisterInput({ onFocus, ...props }, ref) {
    const [locked, setLocked] = useState(true);
    return (
      <Input
        {...props}
        ref={ref}
        readOnly={locked}
        onFocus={(e) => {
          setLocked(false);
          onFocus?.(e);
        }}
      />
    );
  }
);

/**
 * 角色选择器：登录表单与注册弹窗共用，选中态跟随红蓝主色，避免两处样式漂移。
 */
function RolePicker({
  id,
  value,
  onChange
}: {
  id: string;
  value: Role;
  onChange: (role: Role) => void;
}) {
  return (
    <div id={id} className="grid grid-cols-2 gap-2 sm:grid-cols-4">
      {ROLES.map((r) => {
        const active = r.value === value;
        return (
          <button
            key={r.value}
            type="button"
            aria-pressed={active}
            onClick={() => onChange(r.value)}
            className={cn(
              'rounded-control border px-2 py-2 text-xs font-medium transition-colors duration-fast ease-out',
              active
                ? r.team === 'red'
                  ? 'border-red-team bg-red-team text-white'
                  : r.team === 'blue'
                    ? 'border-blue-team bg-blue-team text-white'
                    : 'border-content bg-content text-white'
                : 'border-border bg-white/70 text-content-muted hover:border-border-strong hover:text-content'
            )}
          >
            {r.label}
          </button>
        );
      })}
    </div>
  );
}

/** 漂浮圆角卡片：错落分布 + 不同深度，形成缓慢漂浮与视差（移动端仅保留上沿元素）。 */
interface Floater {
  id: string;
  x: number;
  y: number;
  size: number;
  rotate: number;
  depth: number;
  duration: number;
  delay: number;
  team: 'red' | 'blue';
  focusX: number;
  focusY: number;
  desktopOnly?: boolean;
}

const FLOATERS: Floater[] = [
  { id: 'f1', x: 4, y: 15, size: 148, rotate: -9, depth: 0.56, duration: 13, delay: 0, team: 'red', focusX: 18, focusY: 30, desktopOnly: true },
  { id: 'f2', x: 12, y: 5, size: 92, rotate: 7, depth: 0.3, duration: 15, delay: -3, team: 'blue', focusX: 62, focusY: 22 },
  { id: 'f3', x: 21, y: 31, size: 108, rotate: -5, depth: 0.4, duration: 17, delay: -6, team: 'blue', focusX: 35, focusY: 58, desktopOnly: true },
  { id: 'f4', x: 68, y: 4, size: 96, rotate: 6, depth: 0.28, duration: 16, delay: -8, team: 'red', focusX: 48, focusY: 40 },
  { id: 'f5', x: 79, y: 9, size: 118, rotate: 10, depth: 0.34, duration: 14, delay: -2, team: 'blue', focusX: 75, focusY: 25 },
  { id: 'f6', x: 90, y: 21, size: 152, rotate: -8, depth: 0.58, duration: 12, delay: -5, team: 'red', focusX: 26, focusY: 70, desktopOnly: true },
  { id: 'f7', x: 2, y: 51, size: 116, rotate: 12, depth: 0.5, duration: 15, delay: -4, team: 'blue', focusX: 55, focusY: 45, desktopOnly: true },
  { id: 'f8', x: 94, y: 56, size: 108, rotate: -11, depth: 0.52, duration: 17, delay: -7, team: 'red', focusX: 40, focusY: 60, desktopOnly: true },
  { id: 'f9', x: 7, y: 80, size: 132, rotate: 5, depth: 0.44, duration: 14, delay: -1, team: 'blue', focusX: 30, focusY: 35, desktopOnly: true },
  { id: 'f10', x: 87, y: 82, size: 124, rotate: -6, depth: 0.46, duration: 16, delay: -9, team: 'red', focusX: 60, focusY: 50, desktopOnly: true },
  { id: 'f11', x: 26, y: 92, size: 92, rotate: 9, depth: 0.3, duration: 18, delay: -5, team: 'blue', focusX: 20, focusY: 66, desktopOnly: true },
  { id: 'f12', x: 72, y: 93, size: 100, rotate: -4, depth: 0.32, duration: 15, delay: -2, team: 'red', focusX: 70, focusY: 30, desktopOnly: true }
];

/**
 * 漂浮卡片：外层承担「鼠标视差 + 滚动视差」位移，内层承担缓慢漂浮与轻微倾角，
 * 两层分离避免同一 transform 属性互相覆盖（技术方案 8.7.1 动效预算）。
 */
function FloatingCard({
  floater,
  pointerX,
  progress,
  reduced
}: {
  floater: Floater;
  pointerX: MotionValue<number>;
  progress: MotionValue<number>;
  reduced: boolean;
}) {
  /* 视差一：指针横向移动，深度越大位移越明显 */
  const parallaxX = useTransform(pointerX, (v) => (v - 0.5) * 96 * floater.depth);
  /* 视差二：页面滚动，卡片缓慢上浮 */
  const scrollY = useSpring(useTransform(progress, [0, 1], [0, -150 * floater.depth]), {
    stiffness: 70,
    damping: 22,
    mass: 0.4
  });

  return (
    <motion.div
      aria-hidden="true"
      className={cn('absolute', floater.desktopOnly && 'hidden md:block')}
      style={{ left: `${floater.x}%`, top: `${floater.y}%`, x: parallaxX, y: scrollY }}
    >
      <motion.div
        className="relative overflow-hidden rounded-3xl border border-white/60 shadow-float"
        style={{ width: floater.size, height: Math.round(floater.size * 0.76) }}
        animate={reduced ? undefined : { y: [0, -16, 0], rotate: [floater.rotate, floater.rotate + 2.4, floater.rotate] }}
        transition={{ duration: floater.duration, delay: floater.delay, repeat: Infinity, ease: 'easeInOut' }}
      >
        <div
          className="absolute inset-0 bg-cover opacity-70"
          style={{
            backgroundImage: `url(${ARENA_IMG})`,
            backgroundPosition: `${floater.focusX}% ${floater.focusY}%`,
            backgroundSize: '260%'
          }}
        />
        <div className={cn('absolute inset-0 backdrop-blur-[1px] opacity-[0.14]', floater.team === 'red' ? 'bg-red-team' : 'bg-blue-team')} />
        <div className="absolute inset-0 rounded-3xl ring-1 ring-inset ring-white/45" />
      </motion.div>
    </motion.div>
  );
}

/**
 * 登录首页：顶部导航 + 居中主标题 + 双主按钮 + 简约登录表单（技术方案 8.4 登录态）。
 * 底层背景 = 红蓝机器人对抗擂台图（低透明度 + 高斯模糊 + 降亮度 + 径向蒙版保证文字可读）。
 */
export default function LoginPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const setAuth = useSessionStore((s) => s.setAuth);
  const reduced = useReducedMotion();

  const accountRef = useRef<HTMLInputElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll();
  const pointerRaw = useMotionValue(0.5);
  const pointerX = useSpring(pointerRaw, { stiffness: 55, damping: 20, mass: 0.35 });

  const [account, setAccount] = useState('demo@xian.local');
  const [password, setPassword] = useState('xian-dev');
  const [role, setRole] = useState<Role>('red');
  const [loading, setLoading] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  /* 后端地址设置（APK / 真机评审场景：同源代理不存在，必须显式指定） */
  const [serverOpen, setServerOpen] = useState(false);
  const [serverDraft, setServerDraft] = useState('');
  const [serverProbe, setServerProbe] = useState('');
  const [probing, setProbing] = useState(false);
  const backendBase = getBackendBase();

  /* 注册弹窗：与登录表单同一套极简圆角风格，注册成功后自动进入驾驶舱 */
  const [regOpen, setRegOpen] = useState(false);
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirm, setRegConfirm] = useState('');
  const [regRole, setRegRole] = useState<Role>('red');
  const [regLoading, setRegLoading] = useState(false);
  const [regError, setRegError] = useState('');
  const emailRef = useAutofillSync(regEmail, setRegEmail);
  const passwordRef = useAutofillSync(regPassword, setRegPassword);
  const confirmRef = useAutofillSync(regConfirm, setRegConfirm);

  /* 指针横向视差：仅在未开启「减弱动效」且为精细指针设备时启用 */
  useEffect(() => {
    if (reduced || typeof window === 'undefined') return;
    if (!window.matchMedia('(pointer: fine)').matches) return;
    const onMove = (e: PointerEvent) => pointerRaw.set(e.clientX / window.innerWidth);
    window.addEventListener('pointermove', onMove, { passive: true });
    return () => window.removeEventListener('pointermove', onMove);
  }, [pointerRaw, reduced]);

  /* 点击外部 / Esc 关闭中央菜单 */
  useEffect(() => {
    if (!menuOpen) return;
    const onDocDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('mousedown', onDocDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDocDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  const focusAccount = useCallback(() => {
    accountRef.current?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' });
    accountRef.current?.focus({ preventScroll: true });
  }, [reduced]);

  const displayName = account.split('@')[0].trim() || '演示管理员';

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await api.post<{ access_token: string }>('/api/v1/auth/login', {
        email: account,
        password,
        tenant_id: DEMO_TENANT
      });
      setAuth({ token: 'xian.token', userId: DEMO_USER_ID, role, email: account, name: displayName, tenantId: DEMO_TENANT });
      toast.success('登录成功', `${ROLES.find((r) => r.value === role)?.label ?? role} · 进入红蓝驾驶舱`);
      navigate('/dashboard', { replace: true });
    } catch {
      /* 离线 / 演示模式：本地写入上下文，保证页面可继续演示（技术方案 8.4） */
      setAuth({ token: 'demo-token', userId: DEMO_USER_ID, role, email: account, name: displayName, tenantId: DEMO_TENANT });
      toast.info('已进入演示模式', '后端未返回登录态，使用本地上下文');
      navigate('/dashboard', { replace: true });
    } finally {
      setLoading(false);
    }
  }

  /** 打开注册弹窗：清空上一次的校验错误，角色默认回到红军。 */
  const openRegister = useCallback(() => {
    setRegError('');
    setRegConfirm('');
    setRegRole('red');
    setRegOpen(true);
  }, []);

  /** 注册：先做本地格式校验，再请求后端注册接口；后端未启动时回退演示态，与登录保持一致。 */
  async function onRegister(e: React.FormEvent) {
    e.preventDefault();
    const email = regEmail.trim().toLowerCase();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
      setRegError('账号需为合法邮箱格式，例如 name@xian.local');
      return;
    }
    if (regPassword.length < 6) {
      setRegError('密码至少 6 位，建议字母与数字组合');
      return;
    }
    if (regPassword !== regConfirm) {
      setRegError('两次输入的密码不一致');
      return;
    }
    setRegLoading(true);
    setRegError('');
    try {
      await api.post<{ access_token: string; role: string }>('/api/v1/auth/register', {
        email,
        password: regPassword,
        role: regRole,
        tenant_id: DEMO_TENANT
      });
      setAuth({
        token: 'xian.token',
        userId: DEMO_USER_ID,
        role: regRole,
        email,
        name: email.split('@')[0] || '新用户',
        tenantId: DEMO_TENANT
      });
      toast.success('注册成功', `${ROLES.find((r) => r.value === regRole)?.label ?? regRole} · 已自动登录`);
      setRegOpen(false);
      navigate('/dashboard', { replace: true });
    } catch (err) {
      /* 后端未启动：本地写入会话，保证演示链路不断（技术方案 8.4） */
      if (err instanceof ApiClientError && err.status === 0) {
        setAuth({
          token: 'demo-token',
          userId: DEMO_USER_ID,
          role: regRole,
          email,
          name: email.split('@')[0] || '新用户',
          tenantId: DEMO_TENANT
        });
        toast.info('已进入演示模式', '后端未启动，注册信息仅在本地生效');
        setRegOpen(false);
        navigate('/dashboard', { replace: true });
        return;
      }
      setRegError(err instanceof Error ? err.message : '注册失败，请稍后重试');
    } finally {
      setRegLoading(false);
    }
  }

  /** 探测后端连通性：直接请求 /healthz，不依赖会话上下文。 */
  async function probeServer(base: string) {
    const url = `${normalizeBase(base)}/healthz`;
    setProbing(true);
    setServerProbe('');
    try {
      const res = await fetch(url, { method: 'GET' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const body = (await res.json()) as { status?: string };
      setServerProbe(`连接正常（status=${body.status ?? 'ok'}）`);
    } catch (err) {
      setServerProbe(`连接失败：${String(err)}`);
    } finally {
      setProbing(false);
    }
  }

  const container = { hidden: {}, show: { transition: { staggerChildren: 0.08, delayChildren: 0.04 } } };  const item = { hidden: { opacity: 0, y: 18 }, show: { opacity: 1, y: 0, transition: { duration: 0.7, ease: EASE } } };

  return (
    <div className="relative min-h-screen bg-base font-sans text-content antialiased" data-theme="light">
      {/* ===== 背景层：红蓝氛围光 + 擂台主题图（低透明度 / 高斯模糊 / 降亮度） + 可读性蒙版 ===== */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -left-40 -top-32 h-[36rem] w-[36rem] rounded-full bg-red-team opacity-20 blur-[120px]" />
        <div className="absolute -bottom-40 -right-32 h-[36rem] w-[36rem] rounded-full bg-blue-team opacity-20 blur-[120px]" />
        <div
          className="absolute inset-0 scale-110 bg-cover bg-center opacity-40 [mask-image:radial-gradient(ellipse_at_50%_42%,transparent_0%,rgba(0,0,0,0.45)_42%,black_100%)]"
          style={{ backgroundImage: `url(${ARENA_IMG})`, filter: 'blur(6px) brightness(0.5) saturate(0.95)' }}
        />
        <div className="absolute inset-0 bg-grid-faint opacity-35 [mask-image:radial-gradient(ellipse_at_50%_50%,black_0%,transparent_72%)]" />
      </div>

      {/* ===== 漂浮卡片层：位于背景图之上、登录表单之下 ===== */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        {FLOATERS.map((f) => (
          <FloatingCard key={f.id} floater={f} pointerX={pointerX} progress={scrollYProgress} reduced={reduced} />
        ))}
      </div>

      <motion.div
        variants={container}
        initial={reduced ? false : 'hidden'}
        animate="show"
        className="relative z-10 flex min-h-screen flex-col"
      >
        {/* ===== 顶部导航：左上两枚入口 · 中央胶囊菜单 · 右上登录入口 ===== */}
        <motion.header variants={item} className="sticky top-0 z-sticky">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-3 px-5 sm:px-8">
            <nav className="flex items-center gap-1">
              {NAV_ITEMS.map((n) => (
                <button
                  key={n.to}
                  type="button"
                  onClick={() => navigate(n.to)}
                  className="rounded-pill border border-transparent px-3.5 py-1.5 text-sm font-medium text-content-muted transition-colors duration-fast ease-out hover:border-border hover:bg-white/60 hover:text-content"
                >
                  {n.label}
                </button>
              ))}
            </nav>

            <div ref={menuRef} className="relative">
              <button
                type="button"
                aria-expanded={menuOpen}
                aria-haspopup="menu"
                onClick={() => setMenuOpen((v) => !v)}
                className={cn(
                  'flex items-center gap-2.5 rounded-pill border border-border bg-white/70 px-2.5 py-1.5 shadow-card backdrop-blur-md transition-colors duration-fast ease-out hover:border-border-strong',
                  menuOpen && 'border-content'
                )}
              >
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M4 7h16M4 12h16M4 17h10" strokeLinecap="round" />
                </svg>
                <span className="text-sm font-medium">菜单</span>
                <span className="relative flex h-5 w-5 items-center justify-center">
                  <span className="absolute inset-0 rounded-full border-2 border-border-strong" />
                  <span className="h-1.5 w-1.5 rounded-full bg-red-team" />
                </span>
              </button>
              {menuOpen ? (
                <motion.div
                  role="menu"
                  initial={{ opacity: 0, y: -8, scale: 0.98 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  transition={{ duration: 0.25, ease: EASE }}
                  className="absolute left-1/2 top-12 w-64 -translate-x-1/2 overflow-hidden rounded-card border border-border bg-white/90 p-1.5 shadow-float backdrop-blur-xl"
                >
                  {MENU_ITEMS.map((m) => (
                    <button
                      key={m.to}
                      type="button"
                      role="menuitem"
                      onClick={() => {
                        setMenuOpen(false);
                        navigate(m.to);
                      }}
                      className="w-full rounded-control px-3 py-2 text-left transition-colors duration-fast ease-out hover:bg-base"
                    >
                      <p className="text-sm font-medium text-content">{m.label}</p>
                      <p className="mt-0.5 text-xs text-content-faint">{m.hint}</p>
                    </button>
                  ))}
                </motion.div>
              ) : null}
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={focusAccount}
                className="rounded-pill border border-transparent px-3.5 py-1.5 text-sm font-medium text-content-muted transition-colors duration-fast ease-out hover:border-border hover:bg-white/60 hover:text-content"
              >
                Login 登录
              </button>
              <button
                type="button"
                aria-label="跳到登录表单"
                onClick={focusAccount}
                className="flex h-9 w-9 items-center justify-center rounded-full border border-border-strong bg-white/70 text-content shadow-card backdrop-blur-md transition-transform duration-fast ease-out hover:scale-105 hover:border-content"
              >
                <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path d="M5 12h14M13 6l6 6-6 6" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </button>
            </div>
          </div>
        </motion.header>

        {/* ===== 居中主体：主标题 + 简介 + 双主按钮 + 登录表单 ===== */}
        <main className="flex flex-1 flex-col items-center justify-center px-5 pb-14 pt-8 sm:px-8 sm:pt-14">
          <motion.h1
            variants={item}
            id="hero"
            className="bg-gradient-to-br from-content to-content-muted bg-clip-text text-center text-[3.5rem] font-extrabold leading-none tracking-tighter text-transparent sm:text-7xl md:text-8xl"
          >
            XIAN
          </motion.h1>

          <motion.p variants={item} className="mt-6 max-w-xl text-center text-sm leading-relaxed text-content-muted sm:text-base">
            红蓝攻防演练平台，一站式网络安全红蓝对抗实战演练系统
          </motion.p>

          <motion.div variants={item} className="mt-9 flex w-full max-w-sm flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <Button
              type="button"
              onClick={focusAccount}
              className="h-11 w-full rounded-pill bg-content px-7 text-white shadow-float transition-opacity duration-fast ease-out hover:opacity-90 sm:w-auto"
            >
              登录系统
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={openRegister}
              className="h-11 w-full rounded-pill border-border-strong bg-white px-7 text-content sm:w-auto"
            >
              注册账号
            </Button>
          </motion.div>

          {/* 登录表单：简约圆角 + 毛玻璃面板，层级高于漂浮卡片 */}
          <motion.form
            variants={item}
            id="login"
            onSubmit={onSubmit}
            className="mt-10 w-[min(26rem,100%)] space-y-4 rounded-card border border-border bg-white/75 p-6 shadow-float backdrop-blur-xl"
          >
            <Field id="account" label="账号" required>
              <Input
                id="account"
                ref={accountRef}
                type="email"
                name="email"
                autoComplete="username"
                placeholder="name@xian.local"
                value={account}
                onChange={(e) => setAccount(e.target.value)}
                required
              />
            </Field>
            <Field id="password" label="密码" required>
              <Input
                id="password"
                type="password"
                name="password"
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </Field>
            <Field id="role" label="演练角色" hint="角色决定权限：红军执行攻击、蓝军负责防守、管理员全量管控。">
              <RolePicker id="role" value={role} onChange={setRole} />
            </Field>
            <Button type="submit" loading={loading} className="h-11 w-full rounded-pill">
              登录
            </Button>
            <p className="text-center text-xs text-content-faint">
              还没有账号？
              <button
                type="button"
                onClick={openRegister}
                className="ml-1 font-medium text-content-muted underline decoration-border-strong underline-offset-4 transition-colors duration-fast ease-out hover:text-content"
              >
                立即注册
              </button>
            </p>
          </motion.form>

          {/* 底部一行小字辅助文本 */}
          <motion.p variants={item} className="mt-8 max-w-lg text-center text-xs leading-relaxed text-content-faint">
            继续登录即表示你已同意《服务条款》与《隐私政策》 · 所有攻击行为均在授权沙箱内闭环执行
          </motion.p>

          {/* 后端地址：移动端 / APK 场景下同源代理不存在，需在此指定服务端 */}
          <motion.div variants={item} className="mt-4 flex items-center justify-center gap-2 text-xs">
            <span className="text-content-faint">
              后端：{backendBase ? backendBase : '同源（开发代理）'}
            </span>
            <button
              type="button"
              onClick={() => {
                setServerDraft(backendBase);
                setServerProbe('');
                setServerOpen(true);
              }}
              className="rounded-pill border border-border bg-white/70 px-3 py-1 font-medium text-content-muted transition-colors duration-fast ease-out hover:border-border-strong hover:text-content"
            >
              服务器设置
            </button>
          </motion.div>
        </main>
      </motion.div>

      {/* ===== 注册弹窗：账号 + 密码 + 确认密码 + 角色，与登录表单同风格 ===== */}
      <Dialog open={regOpen} onOpenChange={setRegOpen}>
        {/* Portal 会把内容挂到 body，脱离登录页的 data-theme，需显式指定浅色主题 */}
        <DialogContent data-theme="light" className="text-content">
          <DialogHeader>
            <DialogTitle>注册账号</DialogTitle>
            <DialogDescription>
              填写邮箱与密码即可创建演练账号，注册成功后自动进入红蓝驾驶舱。
            </DialogDescription>
          </DialogHeader>

          <form id="register" autoComplete="off" onSubmit={onRegister} className="space-y-4">
            <Field id="reg-account" label="账号" required hint="邮箱即登录账号">
              <RegisterInput
                id="reg-account"
                type="email"
                name="reg-email"
                autoComplete="off"
                placeholder="name@xian.local"
                ref={emailRef}
                value={regEmail}
                onChange={(e) => setRegEmail(e.target.value)}
                required
              />
            </Field>
            <Field id="reg-password" label="密码" required error={regError || null} hint="至少 6 位">
              <RegisterInput
                id="reg-password"
                type="password"
                name="reg-password"
                autoComplete="new-password"
                placeholder="••••••••"
                ref={passwordRef}
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                required
              />
            </Field>
            <Field id="reg-confirm" label="确认密码" required>
              <RegisterInput
                id="reg-confirm"
                type="password"
                name="reg-confirm"
                autoComplete="new-password"
                placeholder="再次输入密码"
                ref={confirmRef}
                value={regConfirm}
                onChange={(e) => setRegConfirm(e.target.value)}
                required
              />
            </Field>
            <Field id="reg-role" label="演练角色" hint="角色决定权限：红军执行攻击、蓝军负责防守。">
              <RolePicker id="reg-role" value={regRole} onChange={setRegRole} />
            </Field>
          </form>

          <DialogFooter>
            <Button type="button" variant="outline" disabled={regLoading} onClick={() => setRegOpen(false)}>
              取消
            </Button>
            <Button type="submit" form="register" loading={regLoading}>
              注册并登录
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={serverOpen} onOpenChange={setServerOpen}>
        {/* Portal 会把内容挂到 body，脱离登录页的 data-theme，需显式指定浅色主题 */}
        <DialogContent data-theme="light" className="text-content">
          <DialogHeader>
            <DialogTitle>后端服务器地址</DialogTitle>
            <DialogDescription>
              填写 XIAN 后端服务的地址，例如 http://192.168.1.5:8000。留空表示与前端同源
              （仅开发态由 Vite 代理到 127.0.0.1:8000）。安装为独立 App 后必须填写，
              手机与后端需在同一网络，且后端以 --host 0.0.0.0 启动。
            </DialogDescription>
          </DialogHeader>

          <Field id="backend" label="服务端地址" hint="不含结尾斜杠；示例：http://192.168.1.5:8000">
            <Input
              id="backend"
              value={serverDraft}
              onChange={(e) => setServerDraft(e.target.value)}
              placeholder="http://192.168.1.5:8000"
              autoComplete="off"
            />
          </Field>

          {serverProbe ? (
            <p className="mt-3 text-xs text-content-muted">{serverProbe}</p>
          ) : null}

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              disabled={probing}
              onClick={() => probeServer(serverDraft)}
            >
              {probing ? '检测中…' : '测试连接'}
            </Button>
            <Button
              type="button"
              onClick={() => {
                setBackendBase(serverDraft);
                setServerOpen(false);
                toast.success('后端地址已保存', serverDraft ? serverDraft : '同源（开发代理）');
              }}
            >
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}



