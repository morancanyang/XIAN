import { motion } from 'framer-motion';
import { useReducedMotion } from './useReducedMotion';

export interface PathDrawProps {
  /** SVG path 的 d 属性 */
  d: string;
  stroke?: string;
  strokeWidth?: number;
  className?: string;
  duration?: number;
}

/** 攻击路径描线：GSAP DrawSVG 思路的 stroke-dashoffset 实现（技术方案 8.6）。 */
export function PathDraw({
  d,
  stroke = 'var(--color-blue-team)',
  strokeWidth = 2,
  className,
  duration = 1.2
}: PathDrawProps) {
  const reduced = useReducedMotion();
  if (reduced) {
    return <path d={d} fill="none" stroke={stroke} strokeWidth={strokeWidth} className={className} />;
  }
  return (
    <motion.path
      d={d}
      fill="none"
      stroke={stroke}
      strokeWidth={strokeWidth}
      strokeDasharray="1"
      initial={{ pathLength: 0, opacity: 0 }}
      animate={{ pathLength: 1, opacity: 1 }}
      transition={{ duration, ease: 'easeInOut' }}
      className={className}
    />
  );
}