import { Component, type ErrorInfo, type ReactNode } from 'react';
import { Button } from '../primitives/Button';
import { cn } from '../../lib/cn';

export interface ErrorBoundaryProps {
  children: ReactNode;
  /** 降级 UI 的说明文案；按挂载位置区分层级（全局 / 路由级）。 */
  label?: string;
  className?: string;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * 错误边界（技术方案 8.7.3）：
 * React 渲染期异常若无人接管，会连带卸载整棵组件树，用户看到的就是整页白屏——
 * 侧边栏、顶栏、导航全部消失，且没有任何可恢复入口。
 * 因此全局与每个路由都套一层：异常只吞掉出错的子树，其余界面保持可用，
 * 并给出「重试」与「返回驾驶舱」两个可执行动作。
 */
export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  override state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  override componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('[ErrorBoundary]', this.props.label ?? 'unknown', error, info.componentStack);
  }

  private reset = () => {
    this.setState({ error: null });
  };

  override render() {
    const { error } = this.state;
    if (!error) return this.props.children;

    return (
      <div
        role="alert"
        className={cn(
          'flex min-h-[50vh] flex-col items-center justify-center gap-3 rounded-card border border-danger/40 bg-danger/5 px-6 py-10 text-center',
          this.props.className
        )}
      >
        <p className="text-sm font-semibold text-danger">{this.props.label ?? '界面渲染异常'}</p>
        <p className="max-w-md text-xs text-content-muted">
          该区域加载时出现问题，已停止渲染以避免影响其他功能。可以重试，或返回驾驶舱继续其他操作。
        </p>
        <p className="max-w-md rounded-control bg-elevated px-3 py-2 font-mono text-[11px] text-content-muted">
          {error.message || String(error)}
        </p>
        <div className="flex items-center gap-2">
          <Button size="sm" onClick={this.reset}>
            重试
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              this.reset();
              window.location.assign('/dashboard');
            }}
          >
            返回驾驶舱
          </Button>
        </div>
      </div>
    );
  }
}
