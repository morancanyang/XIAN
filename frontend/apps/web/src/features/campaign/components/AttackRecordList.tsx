import { useCampaignRecords } from '../../../lib/api/hooks';
import { VirtualList, VerdictBadgeLazy, DataTable, Pagination, recordEvidence } from './recordBits';
import { useState } from 'react';
import type { AttackRecord } from '@xian/types';

/** 底部攻击记录列表（技术方案 8.4 模式一）：长列表虚拟化 + 判定徽标弹入。 */
export function AttackRecordList({ campaignId }: { campaignId: string }) {
  const [page, setPage] = useState(1);
  const [size, setSize] = useState(20);
  const [virtual, setVirtual] = useState(true);
  const records = useCampaignRecords(campaignId, page, size);

  if (records.isLoading) return <p className="p-4 text-xs text-content-muted">记录加载中…</p>;

  const rows = records.data?.items ?? [];

  if (rows.length === 0) {
    return <p className="p-4 text-xs text-content-faint">暂无攻击记录。执行战役后此处实时刷新。</p>;
  }

  return (
    <div>
      <div className="mb-2 flex items-center gap-2">
        <span className="text-xs text-content-muted">共 {records.data?.total ?? 0} 条</span>
        <button
          type="button"
          className="ml-auto rounded border border-border px-2 py-0.5 text-[11px] text-content-muted hover:bg-white/10"
          onClick={() => setVirtual((v) => !v)}
        >
          {virtual ? '切换为表格' : '切换为虚拟列表'}
        </button>
      </div>

      {virtual ? (
        <VirtualList
          height={300}
          items={rows}
          rowKey={(r: AttackRecord) => r.id}
          renderRow={(r: AttackRecord) => (
            <div className="mb-1 flex items-center gap-3 rounded-control border border-border bg-elevated px-3 py-2 text-xs">
              <span className="font-mono text-content">{r.case_id}</span>
              <span className="w-16 shrink-0 text-content-faint">{r.category_code}</span>
              <span className="w-24 shrink-0 truncate text-content-muted">{r.strategy}</span>
              <span className="min-w-0 flex-1 truncate text-content-faint" title={recordEvidence(r)}>
                {recordEvidence(r)}
              </span>
              <span className="shrink-0 text-content-faint">{r.turns} 轮</span>
              <VerdictBadgeLazy verdict={r.verdict} />
            </div>
          )}
        />
      ) : (
        <DataTable
          columns={[
            { key: 'case', header: '用例', render: (r) => <span className="font-mono text-xs">{r.case_id}</span> },
            { key: 'category', header: '类别', render: (r) => r.category_code },
            { key: 'strategy', header: '策略', render: (r) => <span className="text-xs">{r.strategy}</span> },
            {
              key: 'evidence',
              header: '判定依据',
              render: (r) => (
                <span className="text-xs text-content-muted" title={recordEvidence(r)}>
                  {recordEvidence(r)}
                </span>
              )
            },
            { key: 'turns', header: '轮次', render: (r) => r.turns },
            { key: 'tokens', header: 'Token', render: (r) => r.tokens },
            { key: 'verdict', header: '判定', render: (r) => <VerdictBadgeLazy verdict={r.verdict} /> }
          ]}
          rows={rows}
          rowKey={(r) => r.id}
        />
      )}

      <Pagination
        page={page}
        size={size}
        total={records.data?.total ?? 0}
        onPageChange={setPage}
        onSizeChange={(s) => {
          setSize(s);
          setPage(1);
        }}
      />
    </div>
  );
}