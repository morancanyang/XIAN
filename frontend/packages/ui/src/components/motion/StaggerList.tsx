import * as React from 'react';
import { motion } from 'framer-motion';
import { useReducedMotion } from './useReducedMotion';

export interface StaggerListProps<T> {
  items: T[];
  renderItem: (item: T, index: number) => React.ReactNode;
  keyOf: (item: T, index: number) => string;
  step?: number;
  className?: string;
  as?: 'ul' | 'div' | 'ol';
}

/** 列表依次入场；事件流插入使用 layout 动画实现「滑入」（技术方案 8.6）。 */
export function StaggerList<T>({
  items,
  renderItem,
  keyOf,
  step = 0.05,
  className,
  as = 'ul'
}: StaggerListProps<T>) {
  const reduced = useReducedMotion();

  const children = items.map((item, i) => renderItem(item, i));

  if (reduced) {
    if (as === 'div') return <div className={className}>{children}</div>;
    if (as === 'ol') return <ol className={className}>{children}</ol>;
    return <ul className={className}>{children}</ul>;
  }

  const item = {
    hidden: { opacity: 0, y: -6 },
    show: { opacity: 1, y: 0, transition: { duration: 0.25, ease: [0.16, 1, 0.3, 1] as const } }
  };
  const container = {
    hidden: {},
    show: { transition: { staggerChildren: step } }
  };

  if (as === 'div') {
    return (
      <motion.div className={className} initial="hidden" animate="show" variants={container}>
        {items.map((it, i) => (
          <motion.div key={keyOf(it, i)} layout variants={item}>
            {renderItem(it, i)}
          </motion.div>
        ))}
      </motion.div>
    );
  }

  if (as === 'ol') {
    return (
      <motion.ol className={className} initial="hidden" animate="show" variants={container}>
        {items.map((it, i) => (
          <motion.li key={keyOf(it, i)} layout variants={item}>
            {renderItem(it, i)}
          </motion.li>
        ))}
      </motion.ol>
    );
  }

  return (
    <motion.ul className={className} initial="hidden" animate="show" variants={container}>
      {items.map((it, i) => (
        <motion.li key={keyOf(it, i)} layout variants={item}>
          {renderItem(it, i)}
        </motion.li>
      ))}
    </motion.ul>
  );
}