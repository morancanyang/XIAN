import { cn } from '../../lib/cn';

export interface GlobalLoadingProps {
  visible: boolean;
  label?: string;
}

/** 全局 loading（PRD 2.3.3）。 */
export function GlobalLoading({ visible, label = '加载中' }: GlobalLoadingProps) {
  if (!visible) return null;
  return (
    <div
      role="status"
      aria-live="polite"
      className={cn(
        'fixed left-1/2 top-1/2 z-alert -translate-x-1/2 -translate-y-1/2',
        'flex items-center gap-3 rounded-card border border-border bg-elevated px-5 py-3 shadow-float'
      )}
    >
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-blue-team border-t-transparent" />
      <span className="text-sm text-content">{label}</span>
    </div>
  );
}