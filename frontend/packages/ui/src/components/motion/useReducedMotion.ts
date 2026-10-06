import { useEffect, useState } from 'react';
import { animate, useMotionValue, useReducedMotion as useFramerReducedMotion } from 'framer-motion';

/**
 * 全局「减弱动效」开关（PRD 2.3.3 / 技术方案 8.1）。
 * 归一化两个来源：localStorage 持久化的用户开关 + 系统 prefers-reduced-motion。
 */
const STORAGE_KEY = 'xian.reduced-motion';

export function useReducedMotion(): boolean {
  const system = useFramerReducedMotion();
  const [manual, setManual] = useState<boolean>(() => {
    if (typeof window === 'undefined') return false;
    return window.localStorage.getItem(STORAGE_KEY) === '1';
  });

  useEffect(() => {
    const onCustom = () => setManual(window.localStorage.getItem(STORAGE_KEY) === '1');
    const onStorage = (e: StorageEvent) => {
      if (e.key === STORAGE_KEY) onCustom();
    };
    window.addEventListener('xian:motion-preference', onCustom);
    window.addEventListener('storage', onStorage);
    return () => {
      window.removeEventListener('xian:motion-preference', onCustom);
      window.removeEventListener('storage', onStorage);
    };
  }, []);

  return system || manual;
}

export function setReducedMotion(value: boolean): void {
  window.localStorage.setItem(STORAGE_KEY, value ? '1' : '0');
  window.dispatchEvent(new CustomEvent('xian:motion-preference'));
}

/** 数字动画：从当前值平滑滚动到目标值（技术方案 8.6「数字变化」600ms）。 */
export function useCountUp(target: number, durationMs = 600): number {
  const reduced = useReducedMotion();
  const mv = useMotionValue(target);
  const [value, setValue] = useState(target);

  useEffect(() => {
    if (reduced) {
      mv.set(target);
      setValue(target);
      return;
    }
    const controls = animate(mv, target, {
      duration: durationMs / 1000,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (latest) => setValue(latest)
    });
    return () => controls.stop();
  }, [target, durationMs, reduced, mv]);

  return value;
}