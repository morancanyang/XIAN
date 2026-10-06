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
}

/**
 * 背景层统一约束（技术方案 8.7.2）：
 * - 固定最底层 `position: fixed` + `z-index: var(--z-backdrop)`（位于 --z-* 体系之下）
 * - `aria-hidden="true"` + `pointer-events: none`，绝不拦截控制台/表格/拖拽
 * - 命中全局「减弱动效」或系统 `prefers-reduced-motion` 时立即降级为静态首帧/纯渐变
 * - 页面不可见（document.visibilityState）时暂停渲染循环
 */
export function BackgroundLayer({
  children,
  fallbackClassName = 'bg-gradient-to-b from-base to-sunken',
  className,
  theme = 'dark'
}: BackgroundLayerProps) {
  const reduced = useReducedMotion();
  const degraded = reduced || theme === 'light';

  return (
    <div
      aria-hidden="true"
      className={cn('pointer-events-none fixed inset-0 overflow-hidden', className)}
      style={{ zIndex: 'var(--z-backdrop)' }}
      data-degraded={degraded ? 'true' : 'false'}
    >
      {degraded ? <div className={cn('h-full w-full', fallbackClassName)} /> : children}
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