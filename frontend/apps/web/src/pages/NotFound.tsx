import { Link } from 'react-router-dom';
import { EmptyState } from '@xian/ui';

export function NotFound() {
  return (
    <div className="flex min-h-screen items-center justify-center p-6">
      <EmptyState
        title="页面不存在"
        description="该路由未在页面清单中登记，可能是链接已失效。"
        action={
          <Link to="/dashboard" className="rounded-control bg-blue-team px-4 py-2 text-sm text-white">
            返回驾驶舱
          </Link>
        }
      />
    </div>
  );
}
