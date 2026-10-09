import { useEffect, useState } from 'react';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Textarea,
  cn
} from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { LevelMap } from '../../features/levels/components/LevelMap';
import { OrbBackdrop } from '../../features/dashboard/components/OrbBackdrop';
import { useHint, useLevelHardening, useLevels, useLevelProgress, useStartLevel, useSubmitLevel } from '../../lib/api/hooks';
import { useToast } from '../../components/layout/ToastHost';
import { errorMessage } from '../../lib/api/errors';
import { useLevelStore } from '../../store/levelStore';
import { useConsoleStore } from '../../store/consoleStore';

/** 十关挑战（技术方案 8.4 关卡地图 + 详情抽屉）。 */
export default function LevelMapPage() {
  const levels = useLevels();
  const progress = useLevelProgress();
  const start = useStartLevel();
  const hint = useHint();
  const submit = useSubmitLevel();
  const currentCode = useLevelStore((s) => s.currentLevel);
  const setCurrentCode = useLevelStore((s) => s.setCurrentLevel);
  const markCompleted = useLevelStore((s) => s.markCompleted);
  const energy = useConsoleStore((s) => s.energy);
  const setEnergy = useConsoleStore((s) => s.setEnergy);
  const toast = useToast();

  const [agentOutput, setAgentOutput] = useState('');
  const [canaryValue, setCanaryValue] = useState('');
  const [systemPrompt, setSystemPrompt] = useState('');
  const [selected, setSelected] = useState<string | null>(currentCode);
  const [pickedTechnique, setPickedTechnique] = useState<string>('');

  const selectedLevel = levels.data?.find((l) => l.id === selected) ?? null;
  // 实际使用的手法：切换关卡后 pickedTechnique 可能已不属于这一关，回落到该关第一种。
  // 之前这里恒取 techniques[0]，后端又只按这一个手法记覆盖度，雷达就永远是按关卡写死的。
  const technique =
    pickedTechnique && selectedLevel?.techniques.includes(pickedTechnique)
      ? pickedTechnique
      : (selectedLevel?.techniques[0] ?? '');
  const selectedProgress = progress.data?.find((p) => p.level_id === selected) ?? null;
  const hardening = useLevelHardening(selected ?? '');

  // 能量按关卡各自记账（后端 level_progress.energy_left）：切换关卡时把徽标同步到
  // 当前关卡的剩余能量，不然它还显示上一关扣过的数值，像没扣一样。
  useEffect(() => {
    setEnergy(selectedProgress?.energy_left ?? 100);
  }, [selectedProgress?.energy_left, setEnergy]);

  return (
    <div>
      <PageHeader
        title="十关挑战"
        description="从提示注入到蜜标外带逐关解锁；提示扣能量，无提示通关可获额外徽章（PRD 3.4.5）。"
        actions={<Badge tone="coach">能量 {energy}</Badge>}
      />

      <div className="grid gap-4 xl:grid-cols-[360px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>关卡地图</CardTitle>
            <Badge tone={progress.data?.length ? 'blue' : 'neutral'}>
              已通关 {progress.data?.filter((p) => p.status === 'passed').length ?? 0} / {levels.data?.length ?? 0}
            </Badge>
          </CardHeader>
          <CardContent>
            {levels.isLoading ? (
              <p className="text-xs text-content-muted">加载中…</p>
            ) : (
              <LevelMap
                levels={levels.data ?? []}
                progress={progress.data ?? []}
                selectedCode={selected}
                onSelect={(lv) => {
                  setSelected(lv.id);
                  setCurrentCode(lv.id);
                  start.mutate(lv.id);
                  hardening.refetch();
                }}
              />
            )}
          </CardContent>
        </Card>

        <Card className="relative overflow-hidden">
          {selectedProgress?.status === 'passed' ? (
            <div className="pointer-events-none absolute inset-0 z-0 opacity-70">
              <OrbBackdrop secScore={selectedProgress.score ?? 100} grade={selectedProgress.score != null && selectedProgress.score >= 90 ? 'S' : (selectedProgress.score ?? 0) >= 75 ? 'A' : 'B'} />
            </div>
          ) : null}
          <CardHeader>
            <CardTitle>{selectedLevel ? selectedLevel.name : '选择左侧关卡开始'}</CardTitle>
            {selectedLevel ? <Badge tone="blue">{selectedLevel.scenario_code}</Badge> : null}
          </CardHeader>
          <CardContent className="space-y-4">
            {selectedLevel ? (
              <>
                <p className="text-sm text-content-muted xian-cjk">{selectedLevel.goal}</p>
                <div>
                  <p className="mb-1 text-xs text-content-muted">本关手法（选中你实际用到的那种，会计入能力雷达）</p>
                  <div className="flex flex-wrap gap-1">
                    {selectedLevel.techniques.map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setPickedTechnique(t)}
                        aria-pressed={technique === t}
                        className={cn(
                          'rounded-pill border px-2 py-0.5 text-xs font-medium transition-colors',
                          technique === t
                            ? 'border-coach/60 bg-coach/15 text-coach'
                            : 'border-border bg-white/5 text-content-muted hover:border-coach/40 hover:text-content'
                        )}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>

                <Tabs defaultValue="submit">
                  <TabsList>
                    <TabsTrigger value="submit">提交成果</TabsTrigger>
                    <TabsTrigger value="hints">三级提示</TabsTrigger>
                    <TabsTrigger value="hardening">加固建议</TabsTrigger>
                  </TabsList>

                  <TabsContent value="submit" className="space-y-3">
                    <label className="block text-xs text-content-muted">
                      Agent 最终输出
                      <Textarea
                        value={agentOutput}
                        onChange={(e) => setAgentOutput(e.target.value)}
                        rows={4}
                        className="mt-1"
                        placeholder="粘贴 Agent 的回复内容…"
                      />
                    </label>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <label className="block text-xs text-content-muted">
                        蜜标值（若命中）
                        <input
                          value={canaryValue}
                          onChange={(e) => setCanaryValue(e.target.value)}
                          className="mt-1 h-10 w-full rounded-control border border-border bg-base px-3 font-mono text-xs"
                        />
                      </label>
                      <label className="block text-xs text-content-muted">
                        系统提示词（若泄露）
                        <input
                          value={systemPrompt}
                          onChange={(e) => setSystemPrompt(e.target.value)}
                          className="mt-1 h-10 w-full rounded-control border border-border bg-base px-3 font-mono text-xs"
                        />
                      </label>
                    </div>
                    <Button
                      loading={submit.isPending}
                      onClick={async () => {
                        if (!selected || !selectedLevel) return;
                        try {
                          const res = await submit.mutateAsync({
                            code: selected,
                            output: agentOutput,
                            system_prompt: systemPrompt,
                            canary_values: canaryValue ? [canaryValue] : [],
                            tokens_used: 0,
                            baseline_tokens: 0,
                            turns: [],
                            tool_calls: [],
                            egress_bodies: [agentOutput],
                            secret_token: canaryValue,
                            secret_fields: canaryValue ? { canary: canaryValue } : {},
                            memory_after_new_session: agentOutput,
                            time_used: 0,
                            technique
                          });
                          if (res.attempt_passed) {
                            markCompleted(res.level_id, res.score);
                            toast.success('通关成功', `${selectedLevel.name} · ${res.score} 分`);
                          } else if (res.status === 'passed') {
                            // 已通关的关卡重复提交：status 还是 passed，但本次判定没过，
                            // 不能拿历史状态再弹一次通关成功。
                            toast.info('该关已通关', `本次未满足通过条件，历史最好成绩 ${res.score} 分`);
                          } else {
                            toast.error('未通关', res.attempt_reason || '请检查是否满足该关的通过条件');
                          }
                          progress.refetch();
                        } catch (e) {
                          toast.error('提交失败', errorMessage(e));
                        }
                      }}
                    >
                      提交并判定
                    </Button>
                    <p className="text-[11px] text-content-faint">
                      后端按关卡 pass_criteria 结构化判定；可一并提交 Agent 输出、蜜标值与泄露的系统提示词。
                    </p>
                  </TabsContent>

                  <TabsContent value="hints" className="space-y-3">
                    {(['H1', 'H2', 'H3'] as const).map((h) => {
                      const used = (selectedProgress?.hints_used ?? []).includes(h);
                      return (
                        <div key={h} className="flex items-start gap-3 rounded-control border border-border bg-elevated p-3">
                          <div className="min-w-0 flex-1">
                            <p className="text-xs font-semibold">{h} 提示</p>
                            {/* 没花钱不展示内容：原先列表里直接截断预览，H3 的近似 payload 等于白给 */}
                            <p className="mt-1 text-[11px] text-content-muted xian-cjk">
                              {used ? (selectedLevel.hints?.[h] ?? '暂无') : '使用后显示'}
                            </p>
                          </div>
                          <Button
                            size="sm"
                            variant="outline"
                            disabled={!selected || used}
                            loading={hint.isPending}
                            onClick={async () => {
                              if (!selected) return;
                              try {
                                const res = await hint.mutateAsync({ code: selected, hint_level: h });
                                setEnergy(res.energy_left);
                                toast.info(
                                  `已使用 ${h} · 扣除 ${res.energy_cost} 能量`,
                                  `剩余能量 ${res.energy_left}：${res.content}`
                                );
                              } catch (e) {
                                toast.error('提示不可用', errorMessage(e));
                              }
                            }}
                          >
                            {used ? '已用' : '使用'}
                          </Button>
                        </div>
                      );
                    })}
                  </TabsContent>

                  <TabsContent value="hardening">
                    <Button variant="outline" onClick={() => hardening.refetch()}>
                      查看加固建议
                    </Button>
                    <pre className="mt-3 max-h-64 overflow-auto rounded-control border border-border bg-sunken p-3 font-mono text-[11px]">
                      {JSON.stringify(hardening.data ?? {}, null, 2)}
                    </pre>
                  </TabsContent>
                </Tabs>
              </>
            ) : (
              <p className="text-sm text-content-faint">从左侧关卡地图选择一关开始。</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}