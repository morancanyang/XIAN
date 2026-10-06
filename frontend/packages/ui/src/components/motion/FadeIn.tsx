import * as React from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from './useReducedMotion';

export interface FadeInProps {
  children: React.ReactNode;
  delay?: number;
  y?: number;
  className?: string;
  as?: 'div' | 'li' | 'section' | 'article';
}

/** 入场淡入。减弱动效时直接渲染静态节点（技术方案 8.6 降级）。 */
export function FadeIn({ children, delay = 0, y = 8, className, as = 'div' }: FadeInProps) {
  const reduced = useReducedMotion();

  if (reduced) {
    if (as === 'li') return <li className={className}>{children}</li>;
    if (as === 'section') return <section className={className}>{children}</section>;
    if (as === 'article') return <article className={className}>{children}</article>;
    return <div className={className}>{children}</div>;
  }

  const motionProps = {
    className,
    initial: { opacity: 0, y },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.25, delay, ease: [0.16, 1, 0.3, 1] as const }
  };

  if (as === 'li') return <motion.li {...motionProps}>{children}</motion.li>;
  if (as === 'section') return <motion.section {...motionProps}>{children}</motion.section>;
  if (as === 'article') return <motion.article {...motionProps}>{children}</motion.article>;
  return <motion.div {...motionProps}>{children}</motion.div>;
}