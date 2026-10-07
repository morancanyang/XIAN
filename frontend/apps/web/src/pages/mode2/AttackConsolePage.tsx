import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Field,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Textarea
} from '@xian/ui';
import { PageHeader } from '../../components/ui/PageHeader';
import { ChatStream } from '../../features/console/components/ChatStream';
import { WeaponTree } from '../../features/console/components/WeaponTree';
import { JudgeBadge } from '../../features/console/components/JudgeBadge';
import { BattleCardList } from '../../features/console/components/BattleCardList';
import { ObservationPanel } from '../../features/console/components/ObservationPanel';
import {
  useAgents,
  useCreateSession,
  useMatrixCases,
  useMatrixCategories,
  useScenarioInstances,
  useSendMessage,
  useSessionMessages
} from '../../lib/api/hooks';
import { useSessionStream } from '../../lib/ws/useSessionStream';
import { useConsoleStore } from '../../store/consoleStore';
import { useSessionStore } from '../../store/sessionStore';
import { useToast } from '../../components/layout/ToastHost';
import { errorMessage } from '../../lib/api/errors';

/** 模式二 AttackConsole（技术方案 8.4）：武器库 / 对话 / 教官面板 + 底部观测面板。 */
export default function AttackConsolePage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const activeAgentId = useSessionStore((s) => s.activeAgentId);
  const setActiveSession = useSessionStore((s) => s.setActiveSession);
  const toast = useToast();

  const agents = useAgents({ page: 1, size: 100 });
  const instances = useScenarioInstances();
  const categories = useMatrixCategories();
  const cases = useMatrixCases();
  const messages = useSessionMessages(sessionId);
  const createSession = useCreateSession();
  const send = useSendMessage();

  const [agentId, setAgentId] = useState(activeAgentId ?? '');
  const [instanceId, setInstanceId] = useState('');
  const [draft, setDraft] = useState('');
  const [selectedCaseId, setSelectedCaseId] = useState('');
  const [pendingCase, setPendingCase] = useState<{ id: string; title: string } | null>(null);

  const stream = useConsoleStore((s) => s.stream);
  const battleCards = useConsoleStore((s) => s.cards);
  const energy = useConsoleStore((s) => s.energy);
  const resetConsole = useConsoleStore((s) => s.reset);

  useSessionStream(sessionId);

  const chosenCase = useMemo(() => cases.data?.find((c) => c.id === selectedCaseId), [cases.data, selectedCaseId]);

  async function ensureSession(): Promise<string | null> {
    if (sessionId) return sessionId;
    if (!agentId) {
      toast.error('请先选择 Agent');
      return null;
    }
    try {
      const created = await createSession.mutateAsync({
        agent_id: agentId,
        scenario_instance_id: instanceId || null,
        mode: 'console',
        goal: '自由攻击'
      });
      setActiveSession(created.id);
      /* 落到带 id 的路由上：否则 useParams 取不到会话，消息列表与 WS 流都不会订阅 */
      navigate(`/console/${created.id}`, { replace: true });
      toast.success('会话已创建');
      return created.id;
    } catch (e) {
      toast.error('创建会话失败', errorMessage(e));
      return null;
    }
  }

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col">
      <PageHeader
        title="模式二 · 自由攻击"
        description="武器库选模板 → 对话下发 → 裁判即时判定 → 战报卡片。SSE 流式返回 token。"
        actions={
          <>
            <Badge tone={sessionId ? 'success' : 'neutral'}>{sessionId ? '会话运行中' : '未开始'}</Badge>
            <Badge tone="coach">能量 {energy}</Badge>
            {sessionId ? (
              <Button size="sm" variant="outline" onClick={() => resetConsole()}>
                清理本地缓冲
              </Button>
            ) : null}
          </>
        }
      />

      <PanelGroup direction="horizontal" className="min-h-0 flex-1 rounded-card border border-border bg-elevated/40">
        <Panel defaultSize={22} minSize={16}>
          <div className="flex h-full flex-col">
            <div className="border-b border-border px-3 py-2">
              <p className="text-xs font-semibold">武器库（{cases.data?.length ?? 0} 条用例）</p>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto p-2 xian-scrollbar">
              {categories.isLoading || cases.isLoading ? (
                <p className="text-xs text-content-muted">加载中…</p>
              ) : (
                <WeaponTree
                  categories={categories.data ?? []}
                  cases={cases.data ?? []}
                  onPick={(c) => {
                    setSelectedCaseId(c.id);
                    setPendingCase({ id: c.id, title: c.title });
                  }}
                />
              )}
            </div>
          </div>
        </Panel>

        <PanelResizeHandle className="w-1 bg-border transition-colors hover:bg-blue-team" />

        <Panel defaultSize={50} minSize={30}>
          <div className="flex h-full flex-col">
            <div className="min-h-0 flex-1 p-3">
              <ChatStream messages={messages.data ?? []} />
            </div>
            <div className="border-t border-border p-3">
              {pendingCase ? (
                <div className="mb-2 flex items-center gap-2 rounded-control border border-blue-team/40 bg-blue-team/5 px-2 py-1.5 text-[11px]">
                  <span className="font-mono text-blue-team">{pendingCase.id}</span>
                  <span className="truncate text-content-muted">{pendingCase.title}</span>
                  <button className="ml-auto text-content-faint hover:text-content" onClick={() => setPendingCase(null)}>
                    移除
                  </button>
                </div>
              ) : null}
              <Textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                placeholder="输入攻击载荷，或从左侧武器库选择模板…"
                rows={3}
              />
              <div className="mt-2 flex items-center gap-2">
                <Button
                  size="sm"
                  disabled={!draft.trim()}
                  loading={send.isPending}
                  onClick={async () => {
                    const sid = await ensureSession();
                    if (!sid) return;
                    try {
                      await send.mutateAsync({
                        sessionId: sid,
                        body: { content: draft, case_id: selectedCaseId || null }
                      });
                      setDraft('');
                      messages.refetch();
                    } catch (e) {
                      toast.error('发送失败', errorMessage(e));
                    }
                  }}
                >
                  发送
                </Button>
                {chosenCase ? <span className="text-[11px] text-content-faint">命中判定由结构化裁判 + LLM 仲裁完成</span> : null}
              </div>
            </div>
          </div>
        </Panel>

        <PanelResizeHandle className="w-1 bg-border transition-colors hover:bg-blue-team" />

        <Panel defaultSize={28} minSize={20}>
          <div className="flex h-full flex-col gap-3 overflow-y-auto p-3 xian-scrollbar">
            <Card>
              <CardHeader>
                <CardTitle>教官面板</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 text-xs">
                <Field label="目标 Agent" id="c-agent">
                  <Select value={agentId} onValueChange={setAgentId}>
                    <SelectTrigger id="c-agent">
                      <SelectValue placeholder="选择 Agent" />
                    </SelectTrigger>
                    <SelectContent>
                      {agents.data?.items.map((a) => (
                        <SelectItem key={a.id} value={a.id}>
                          {a.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field
                  label="关联场景实例"
                  id="c-instance"
                  hint="选中沙箱实例后，载荷会打到实例内的靶场 Agent；留空则直连所选 Agent。"
                >
                  <Select value={instanceId} onValueChange={setInstanceId}>
                    <SelectTrigger id="c-instance">
                      <SelectValue placeholder="不关联" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="">不关联</SelectItem>
                      {(instances.data ?? []).map((i) => (
                        <SelectItem key={i.id} value={i.id}>
                          {i.id.slice(0, 12)}（{i.status}）
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </Field>
                <Field label="判定阈值提示" id="c-note" hint="黄金信号优先，其次分类器，最后 LLM 仲裁。">
                  <Input id="c-note" readOnly value="golden > classifier > llm" className="font-mono text-[11px]" />
                </Field>
                <div>
                  <p className="mb-1 text-content-faint">最近判定</p>
                  <div className="space-y-1">
                    {stream.slice(-4).reverse().map((e, i) => (
                      <div key={`${e.ts}-${i}`} className="rounded-control border border-border bg-sunken px-2 py-1.5">
                        <JudgeBadge
                          verdict={String(e.payload?.verdict ?? e.type)}
                          confidence={Number(e.payload?.confidence ?? 0) || undefined}
                          reason={String(e.payload?.reason ?? '')}
                        />
                      </div>
                    ))}
                    {stream.length === 0 ? <p className="text-content-faint">暂无判定</p> : null}
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>战报卡片</CardTitle>
                <Badge tone="danger">{battleCards.length}</Badge>
              </CardHeader>
              <CardContent>
                <BattleCardList cards={battleCards} />
              </CardContent>
            </Card>
          </div>
        </Panel>
      </PanelGroup>

      <div className="mt-3">
        <ObservationPanel events={stream} />
      </div>
    </div>
  );
}
