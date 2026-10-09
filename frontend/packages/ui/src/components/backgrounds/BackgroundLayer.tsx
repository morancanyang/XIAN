import * as React from 'react';
import { cn } from '../../lib/cn';
import { useReducedMotion } from '../motion/useReducedMotion';

export interface BackgroundLayerProps {
  children: React.ReactNode;
  /** 静态降级时渲染的背景（CSS 渐变） */
  fallbackClassName?: string;
  className?: string;
  /** 主题：浅色主题一律退化为纯色，不初始化渲染循环 */
  theme?: 'dark' | 'light';
  /**
   * 内联模式：相对最近的定位祖先铺满，而不是钉在整个视口。
   *
   * 默认 false 保持既有行为 —— Aurora / DarkVeil / Particles 等整页氛围背景都依赖
   * fixed + --z-backdrop。要把背景收进某张卡片内部时必须显式打开：fixed 会绕过
   * 卡片的 overflow-hidden 直接铺到全屏，父级给的 z-index 也管不住它，结果就是
   * 一张卡里冒出个占满屏幕的大光环（关卡结算卡踩过这个坑）。
   */
  inline?: boolean;
}

/**
 * 背景层统一约束（技术方案 8.7.2）：
 * - 默认固定最底层 `position: fixed` + `z-index: var(--z-backdrop)`（位于 --z-* 体系之下）
 * - `inline` 时改为相对定位祖先铺满，供卡片内嵌装饰使用（见 BackgroundLayerProps.inline）
 * - `aria-hidden="true"` + `pointer-events: none`，绝不拦截控制台/表格/拖拽
 * - 命中全局「减弱动效」或系统 `prefers-reduced-motion` 时立即降级为静态首帧/纯渐变
 * - 页面不可见（document.visibilityState）时暂停渲染循环
 */
export function BackgroundLayer({
  children,
  fallbackClassName = 'bg-gradient-to-b from-base to-sunken',
  className,
  theme = 'dark',
  inline = false
}: BackgroundLayerProps) {
  const reduced = useReducedMotion();
  const degraded = reduced || theme === 'light';

  return (
    <div
      aria-hidden="true"
      className={cn(
        'pointer-events-none overflow-hidden',
        inline ? 'absolute inset-0' : 'fixed inset-0',
        className
      )}
      style={inline ? undefined : { zIndex: 'var(--z-backdrop)' }}
      data-degraded={degraded ? 'true' : 'false'}
    >
      {/* 内联降级不能铺 opaque 渐变：那是给整页背景用的，盖在卡片上会糊成一片。 */}
      {degraded ? (
        <div className={cn('h-full w-full', inline ? 'bg-transparent' : fallbackClassName)} />
      ) : (
        children
      )}
    </div>
  );
}

/** 统一读取 Design Token 中的颜色值，避免在背景组件里硬编码色值。 */
export function useTokens(): { red: string; blue: string; coach: string; base: string; border: string } {
  return React.useMemo(() => {
    const read = (name: string, fallback: string) => {
      if (typeof window === 'undefined') return fallback;
      const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
      return v || fallback;
    };
    return {
      red: read('--color-red-team', '#ef4444'),
      blue: read('--color-blue-team', '#3b82f6'),
      coach: read('--color-coach', '#f59e0b'),
      base: read('--bg-base', '#0b0f17'),
      border: read('--border', '#1f2937')
    };
  }, []);
}

let webglSupport: boolean | null = null;

/**
 * 探测 WebGL 可用性并缓存结果。
 *
 * 部分内嵌 WebView / 老旧驱动 / 远程桌面环境拿不到 WebGL 上下文，
 * ogl 的 Renderer 会抛 "unable to create webgl context"。
 * 背景层属于纯装饰，探测失败时必须静默降级，绝不能把异常抛给 React——
 * 否则没有错误边界时整棵树会被卸载，用户看到的就是整页白屏。
 */
export function isWebGLAvailable(): boolean {
  if (webglSupport !== null) return webglSupport;
  if (typeof document === 'undefined') {
    webglSupport = false;
    return webglSupport;
  }
  try {
    const canvas = document.createElement('canvas');
    const gl =
      canvas.getContext('webgl2') ??
      canvas.getContext('webgl') ??
      canvas.getContext('experimental-webgl');
    webglSupport = Boolean(gl);
  } catch {
    webglSupport = false;
  }
  return webglSupport;
}

/** WebGL 能力探测的 React 封装：不可用时组件直接走静态降级分支。 */
export function useWebGLSupport(): boolean {
  const supported = isWebGLAvailable();
  return supported;
}

/** 页面不可见时暂停 rAF，节省 GPU 与电量（8.7.2 性能预算）。 */
export function useVisibility(): boolean {
  const [visible, setVisible] = React.useState(() =>
    typeof document === 'undefined' ? true : document.visibilityState === 'visible'
  );
  React.useEffect(() => {
    const onChange = () => setVisible(document.visibilityState === 'visible');
    document.addEventListener('visibilitychange', onChange);
    return () => document.removeEventListener('visibilitychange', onChange);
  }, []);
  return visible;
}