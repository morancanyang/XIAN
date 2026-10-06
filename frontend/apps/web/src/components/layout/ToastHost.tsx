import * as React from 'react';
import { ToastViewport, type ToastItem, type ToastTone } from '@xian/ui';

interface ToastContextValue {
  success: (title: string, description?: string) => void;
  error: (title: string, description?: string) => void;
  info: (title: string, description?: string) => void;
  dismiss: (id: string) => void;
}

const ToastContext = React.createContext<ToastContextValue | null>(null);

/** PRD 2.3.3：成功用 toast，失败用弹窗。同一时刻最多堆叠 3 条。 */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = React.useState<ToastItem[]>([]);

  const push = React.useCallback((title: string, description?: string, tone: ToastTone = 'info') => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    setToasts((prev) => [{ id, title, description, tone }, ...prev].slice(0, 3));
  }, []);

  const value = React.useMemo<ToastContextValue>(
    () => ({
      success: (title, description) => push(title, description, 'success'),
      error: (title, description) => push(title, description, 'error'),
      info: (title, description) => push(title, description, 'info'),
      dismiss: (id) => setToasts((prev) => prev.filter((t) => t.id !== id))
    }),
    [push]
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={value.dismiss} />
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = React.useContext(ToastContext);
  if (!ctx) throw new Error('useToast 必须在 ToastProvider 内使用');
  return ctx;
}