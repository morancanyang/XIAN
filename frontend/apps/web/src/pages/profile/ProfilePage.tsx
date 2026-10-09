import { Badge, Card, CardContent, CardHeader, CardTitle, Progress } from '@xian/ui';
import '../../styles/profile-fx.css';
import { PageHeader } from '../../components/ui/PageHeader';
import { OrbBackdrop } from '../../features/dashboard/components/OrbBackdrop';
import { RadarScore } from '@xian/ui';
import { useLevelProgress, useProfile } from '../../lib/api/hooks';
import { TableSkeleton } from '../../components/ui/Loading';
import { useLevelStore } from '../../store/levelStore';

/** 个人中心：雷达图 + 段位进度 + 徽章墙（技术方案 8.4）。 */
export default function ProfilePage() {
  const profile = useProfile();
  const progress = useLevelProgress();
  const badges = useLevelStore((s) => s.badges);

  if (profile.isLoading) return <TableSkeleton rows={4} />;

  const radar = profile.data?.radar ?? {};
  const tier = profile.data?.tier ?? 'bronze';
  const points = profile.data?.points ?? 0;
  // 段位阶梯由后端 TIERS 统一算，前端不再各自硬编码阈值
  const nextTier = profile.data?.next_tier ?? null;
  const toNext = profile.data?.points_to_next_tier ?? 0;
  const tierProgress = profile.data?.tier_progress ?? 0;

  return (
    <div className="relative">
      {/* 氛围层：纤细柔光环 + 星云中心 + 底部弥散扫描光带（纯装饰，不参与布局） */}
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="xian-ring-halo fixed inset-x-0 top-0 h-[46rem]" />
        <OrbBackdrop
          secScore={Math.min(100, points / 10)}
          grade={tier === 'gold' ? 'S' : tier === 'silver' ? 'A' : 'B'}
          opacity={0.7}
          timeScale={0.4}
          className="xian-ring-soft"
        />
        <div className="xian-nebula-core fixed left-1/2 top-[34rem] h-[36rem] w-[36rem] -translate-x-1/2 -translate-y-1/2" />
        <div className="xian-scan-layer fixed inset-x-0 bottom-0 h-[38vh]">
          <div className="xian-scan-band absolute inset-x-0 bottom-16 h-14" />
          <div className="xian-scan-flow absolute inset-x-0 bottom-10 h-40" />
          <div className="xian-scan-motes absolute inset-x-0 bottom-8 h-32" />
        </div>
      </div>

      <div className="relative">
        <PageHeader
          title="个人中心"
          description="能力画像、段位进度与徽章墙；数据来自关卡进度聚合。"
          actions={<Badge tone="coach">段位 {tier}</Badge>}
        />

        <div className="grid gap-4 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>能力雷达</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col items-center">
              <RadarScore data={radar} size={260} />
              <p className="mt-2 text-xs text-content-muted">累计积分 {points}</p>
              {Object.values(radar).every((v) => Number(v) === 0) ? (
                <p className="mt-1 text-center text-[11px] leading-relaxed text-content-faint">
                  暂无能力数据：雷达由「十关挑战」通关进度聚合，通关对应关卡后按手法归并到六个能力维度。
                </p>
              ) : null}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>段位进度</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <Progress value={tierProgress} tone="coach" soft />
              <p className="text-xs text-content-muted">
                当前段位 <span className="font-mono text-coach">{tier}</span>，
                {nextTier ? `再获得 ${toNext} 积分晋级 ${nextTier}。` : '已是最高段位。'}
              </p>
              <div className="space-y-2 text-xs">
                {(progress.data ?? []).slice(0, 8).map((p) => (
                  <div key={p.id} className="flex items-center justify-between rounded-control border border-border bg-elevated px-2 py-1.5">
                    <span className="font-mono">{p.level_id}</span>
                    <span className="text-content-muted">{p.status}</span>
                    <span className="font-mono">{p.score} 分</span>
                  </div>
                ))}
                {progress.isLoading ? <TableSkeleton rows={3} /> : null}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>徽章墙</CardTitle>
              <Badge tone="blue">{(profile.data?.badges ?? badges).length}</Badge>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {(profile.data?.badges ?? badges).map((b) => (
                  <span
                    key={b}
                    className="xian-badge-pop rounded-pill border border-coach/40 bg-coach/10 px-3 py-1 text-xs text-coach"
                  >
                    {b}
                  </span>
                ))}
                {(profile.data?.badges ?? badges).length === 0 ? (
                  <p className="text-xs text-content-faint">暂无徽章，通关关卡即可解锁。</p>
                ) : null}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
