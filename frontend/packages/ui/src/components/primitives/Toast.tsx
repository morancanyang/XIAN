import * as ToastPrimitive from '@radix-ui/react-toast';
import { cn } from '../../lib/cn';

export type ToastTone = 'success' | 'error' | 'info';

export interface ToastItem {
  id: string;
  title: string;
  description?: string;
  tone?: ToastTone;
}

export interface ToastViewportProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

const toneIcon: Record<ToastTone, string> = {
  success: '✓',
  error: '!',
  info: 'i'
};

/**
 * Toast 宿主（PRD 2.3.3：成功用 toast，失败用弹窗）。
 * 由 `ToastProvider` 托管，业务代码只调用 `useToast()`。
 */
export function ToastViewport({ toasts, onDismiss }: ToastViewportProps) {
  return (
    <ToastPrimitive.Provider swipeDirection="right">
      {toasts.map((t) => (
        <ToastPrimitive.Root
          key={t.id}
          duration={4200}
          onOpenChange={(open) => {
            if (!open) onDismiss(t.id);
          }}
          className={cn(
            'flex items-start gap-3 rounded-card border bg-elevated p-3 shadow-float',
            t.tone === 'success' && 'border-success/40',
            t.tone === 'error' && 'border-danger/40',
            (!t.tone || t.tone === 'info') && 'border-border'
          )}
        >
          <span
            aria-hidden="true"
            className={cn(
              'mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white',
              t.tone === 'success' && 'bg-success',
              t.tone === 'error' && 'bg-danger',
              (!t.tone || t.tone === 'info') && 'bg-blue-team'
            )}
          >
            {toneIcon[t.tone ?? 'info']}
          </span>
          <div className="min-w-0 flex-1">
            <p className="text-sm font-medium text-content">{t.title}</p>
            {t.description ? <p className="mt-0.5 text-xs text-content-muted">{t.description}</p> : null}
          </div>
        </ToastPrimitive.Root>
      ))}
      <ToastPrimitive.Viewport className="fixed bottom-4 right-4 z-toast flex w-[min(360px,calc(100vw-2rem))] flex-col gap-2" />
    </ToastPrimitive.Provider>
  );
}