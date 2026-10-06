import { useMemo, useState } from 'react';
import {
  Badge,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CodeBlock,
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger
} from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { GridScanBackdrop } from '../../features/matrix/components/GridScanBackdrop';
import { HeatGrid } from '@xian/ui';
import { TableSkeleton } from '../../components/ui/Loading';
import { ErrorState } from '@xian/ui';
import { useMatrixCategories, useMatrixCases, useMatrixCoverage, useMatrixFrameworks } from '../../lib/api/hooks';
import { errorHint, errorMessage } from '../../lib/api/errors';
import { DIFFICULTY_LABEL, SEVERITY_LABEL } from '@xian/types';
import { DataTable, type Column } from '@xian/ui';
import type { AttackCase } from '@xian/types';

const STAGES = ['侦察', '注入', '越权', '外带', '持久化', '横向移动'];

/** 攻击矩阵（技术方案 8.4）：类别 × 阶段热力网格 + 用例详情抽屉。 */
export default function MatrixPage() {
  const categories = useMatrixCategories();
  const cases = useMatrixCases();
  const coverage = useMatrixCoverage();
  const frameworks = useMatrixFrameworks();
  const [openCase, setOpenCase] = useState<AttackCase | null>(null);

  const cells = useMemo(() => {
    const out: { x: string; y: string; value: number; hint: string }[] = [];
    for (const cat of categories.data ?? []) {
      for (const stage of STAGES) {
        const stageHits = cat.techniques.filter((t) => t.includes(stage)).length;
        const ratio = cat.techniques.length ? stageHits / cat.techniques.length : 0;
        out.push({
          x: stage,
          y: `${cat.code}`,
          value: ratio,
          hint: `${cat.code} ${cat.name} × ${stage}：命中 ${stageHits} 项技术`
        });
      }
    }
    return out;
  }, [categories.data]);

  const columns: Column<AttackCase>[] = [
    { key: 'id', header: '用例编号', render: (c) => <span className="font-mono text-xs">{c.id}</span> },
    { key: 'title', header: '标题', render: (c) => c.title },
    { key: 'category', header: '类别', render: (c) => <Badge tone="blue">{c.category_id}</Badge> },
    { key: 'severity', header: '严重度', render: (c) => <span className="text-xs">{SEVERITY_LABEL[c.severity]}</span> },
    { key: 'difficulty', header: '难度', render: (c) => <span className="text-xs">{DIFFICULTY_LABEL[c.difficulty]}</span> },
    { key: 'rate', header: '成功率', render: (c) => <span className="font-mono text-xs">{Math.round(c.success_rate * 100)}%</span> },
    {
      key: 'action',
      header: '',
      render: (c) => (
        <button type="button" className="text-xs text-blue-team hover:underline" onClick={() => setOpenCase(c)}>
          详情
        </button>
      )
    }
  ];

  return (
    <div className="relative">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <GridScanBackdrop />
      </div>

      <PageHeader
        title="攻击矩阵"
        description="14 类攻击面 × 6 阶段技术覆盖；覆盖率达标的类别才允许宣称具备相应检测/防护能力（PRD 3.5.4）。"
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>类别 × 阶段热力网格</CardTitle>
            <Badge tone="blue">{categories.data?.length ?? 0} 类</Badge>
          </CardHeader>
          <CardContent>
            {categories.isLoading ? (
              <TableSkeleton rows={4} />
            ) : categories.isError ? (
              <ErrorState message={errorMessage(categories.error)} hint={errorHint(categories.error)} onRetry={() => categories.refetch()} />
            ) : (
              <HeatGrid
                xLabels={STAGES}
                yLabels={(categories.data ?? []).map((c) => c.code)}
                cells={cells}
                onCellClick={(cell) => setOpenCase(cases.data?.find((c) => c.category_id === cell.y) ?? null)}
              />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>覆盖度统计</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-72 overflow-auto rounded-control border border-border bg-sunken p-3 font-mono text-[11px]">
              {JSON.stringify(coverage.data ?? {}, null, 2)}
            </pre>
          </CardContent>
        </Card>
      </div>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>用例清单</CardTitle>
          <Badge tone="coach">{cases.data?.length ?? 0} 条</Badge>
        </CardHeader>
        <CardContent>
          {cases.isLoading ? (
            <TableSkeleton rows={8} />
          ) : (
            <DataTable
              columns={columns}
              rows={cases.data ?? []}
              rowKey={(c) => c.id}
              emptyTitle="用例库为空"
              emptyDescription="执行 xian seed 导入种子用例。"
              maxRows={100}
            />
          )}
        </CardContent>
      </Card>

      <Card className="mt-4">
        <CardHeader>
          <CardTitle>框架映射</CardTitle>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="frameworks">
            <TabsList>
              <TabsTrigger value="frameworks">框架</TabsTrigger>
              <TabsTrigger value="detail">用例详情</TabsTrigger>
            </TabsList>
            <TabsContent value="frameworks">
              <pre className="max-h-64 overflow-auto rounded-control border border-border bg-sunken p-3 font-mono text-[11px]">
                {JSON.stringify(frameworks.data ?? [], null, 2)}
              </pre>
            </TabsContent>
            <TabsContent value="detail">
              {openCase ? (
                <div className="space-y-3">
                  <p className="text-sm font-semibold">{openCase.title}</p>
                  <div className="flex flex-wrap gap-1">
                    {openCase.scenario_tags.map((t) => (
                      <Badge key={t}>{t}</Badge>
                    ))}
                  </div>
                  <CodeBlock>{openCase.payload_template}</CodeBlock>
                  <p className="text-[11px] text-content-faint">
                    判定提示词：{openCase.judge_prompt || '（使用默认结构化判定）'}
                  </p>
                </div>
              ) : (
                <p className="text-xs text-content-faint">点击用例清单中的「详情」查看载荷模板与判定提示词。</p>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      <Dialog open={Boolean(openCase)} onOpenChange={(v) => !v && setOpenCase(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{openCase?.title}</DialogTitle>
          </DialogHeader>
          {openCase ? (
            <div className="space-y-3">
              <CodeBlock>{openCase.payload_template}</CodeBlock>
              <p className="text-[11px] text-content-faint">贡献者：{openCase.contributor} · v{openCase.version}</p>
            </div>
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  );
}