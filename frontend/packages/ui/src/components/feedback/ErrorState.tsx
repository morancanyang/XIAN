import { Button } from '../primitives/Button';
import { cn } from '../../lib/cn';

export interface ErrorStateProps {
  title?: string;
  message?: string;
  hint?: string;
  onRetry?: () => void;
  className?: string;
}

/** 失败态（PRD 2.3.3：失败用弹窗/显式错误卡片，附可执行提示）。 */
export function ErrorState({
  title = '请求失败',
  message = '服务暂时不可用，请稍后重试。',
  hint,
  onRetry,
  className
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={cn('flex flex-col items-center gap-3 rounded-card border border-danger/40 bg-danger/5 px-6 py-8 text-center', className)}
    >
      <p className="text-sm font-semibold text-danger">{title}</p>
      <p className="max-w-md text-xs text-content-muted">{message}</p>
      {hint ? <p className="max-w-md rounded-control bg-elevated px-3 py-2 font-mono text-[11px] text-content-muted">{hint}</p> : null}
      {onRetry ? (
        <Button variant="outline" size="sm" onClick={onRetry}>
          重试
        </Button>
      ) : null}
    </div>
  );
}