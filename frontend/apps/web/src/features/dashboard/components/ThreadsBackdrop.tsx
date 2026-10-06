import { Threads } from '@xian/ui';

  /** 默认全局背景：App.tsx 根布局最外层（技术方案 8.7.1）。 */
export function ThreadsBackdrop({ className }: { className?: string }) {
  return <Threads className={className} />;
}
