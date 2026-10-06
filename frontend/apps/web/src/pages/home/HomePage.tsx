import { Link } from 'react-router-dom';
import { AuroraBackdrop } from '../../features/dashboard/components/AuroraBackdrop';
import { ParticlesBackdrop } from '../../features/dashboard/components/ParticlesBackdrop';
import { DashboardMetrics } from '../../features/dashboard/components/DashboardMetrics';
import { EventStream } from '../../features/dashboard/components/EventStream';
import { LiveChart } from '@xian/ui';
import { Card, CardContent, CardHeader, CardTitle } from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { useTrend } from '../../lib/api/hooks';

/** 驾驶舱 Home（技术方案 8.4）：顶部 4 指标卡 + 左趋势图 + 右实时事件流。 */
export default function HomePage() {
  const trend = useTrend();
  const labels = trend.data?.map((p) => p.ts.slice(5, 16)) ?? [];
  const series = trend.data?.length
    ? { SecScore: trend.data.map((p) => p.sec_score) }
    : { SecScore: [0] };

  return (
    <div className="relative">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-64 overflow-hidden">
        <AuroraBackdrop />
        <ParticlesBackdrop />
      </div>

      <div className="relative">
        <PageHeader
          title="驾驶舱"
          description="一屏看清纳管资产、进行中战役与最新安全水位；事件流为 WebSocket 实时推送。"
          actions={
            <Link
              to="/agents"
              className="rounded-control bg-blue-team px-4 py-2 text-sm font-medium text-white hover:bg-blue-team/90"
            >
              接入 Agent
            </Link>
          }
        />

        <DashboardMetrics />

        <div className="mt-4 grid gap-4 xl:grid-cols-[2fr_1fr]">
          <Card>
            <CardHeader>
              <CardTitle>SecScore 趋势</CardTitle>
            </CardHeader>
            <CardContent>
              <LiveChart labels={labels.length ? labels : ['无数据']} series={series} height={260} />
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>实时事件流</CardTitle>
            </CardHeader>
            <CardContent>
              <EventStream />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}