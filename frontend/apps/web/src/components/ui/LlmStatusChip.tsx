import { Link } from 'react-router-dom';
import { cn } from '../../lib/utils/cn';
import { useLlmStatus } from '../../lib/api/hooks';

/**
 * 顶栏大模型接入状态灯（技术方案 7.2）。
 * 只读一次网关快照：已接入 / 未接入 / 熔断降级，点击跳管理端配置。
 */
export function LlmStatusChip({ className }: { className?: string }) {
  const status = useLlmStatus();
  const data = status.data;

  if (!data) {
    return (
      <span
        className={cn('flex items-center gap-1.5 text-content-faint', className)}
        title="大模型网关状态加载中"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-coach" />
        大模型 检测中
      </span>
    );
  }

  const online = data.configured && !data.offline;
  const degraded = data.configured && data.offline;
  const label = online ? '大模型已接入' : degraded ? '大模型降级' : '大模型未接入';
  const tone = online ? 'bg-success' : degraded ? 'bg-warning' : 'bg-content-faint';
  const hint = online
    ? `${data.provider} · ${data.models.judge || data.models.redteam} · ${data.online_calls}/${data.calls} 次在线调用`
    : degraded
      ? data.last_error || '连续失败已触发熔断，暂时走离线回放'
      : '未配置 XIAN_LLM_BASE_URL / XIAN_LLM_API_KEY，当前走确定性离线回放';

  return (
    <Link
      to="/admin"
      className={cn('flex items-center gap-1.5 transition-colors duration-fast hover:text-content', className)}
      title={hint}
    >
      <span className={cn('h-1.5 w-1.5 rounded-full', tone)} />
      {label}
    </Link>
  );
}