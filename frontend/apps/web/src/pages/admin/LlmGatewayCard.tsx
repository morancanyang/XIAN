import { useState } from 'react';
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Field,
  Input,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '@xian/ui';
import { useLlmConfig, useLlmProbe, useLlmProviders, useLlmStatus } from '../../lib/api/hooks';
import { errorHint, errorMessage } from '../../lib/api/errors';
import { useToast } from '../../components/layout/ToastHost';

const PROVIDER_LABEL: Record<string, string> = {
  deepseek: 'DeepSeek',
  moonshot: 'Moonshot (Kimi)',
  dashscope: '阿里 DashScope (Qwen)',
  siliconflow: 'SiliconFlow',
  zhipu: '智谱 GLM',
  openai: 'OpenAI'
};

/** 大模型接入配置卡：四角色模型路由 + 连通性探测（技术方案 7.2）。 */
export function LlmGatewayCard() {
  const status = useLlmStatus();
  const providers = useLlmProviders();
  const probe = useLlmProbe();
  const save = useLlmConfig();
  const toast = useToast();

  const [provider, setProvider] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [judgeModel, setJudgeModel] = useState('');
  const [targetModel, setTargetModel] = useState('');

  const data = status.data;
  const online = data?.configured && !data?.offline;

  function submit() {
    save.mutate(
      {
        provider,
        base_url: baseUrl,
        api_key: apiKey,
        judge_model: judgeModel,
        target_model: targetModel
      },
      {
        onSuccess: (res) => {
          if (res.probe.ok) {
            toast.success('大模型接入已生效', `${res.provider} · ${res.probe.latency_ms}ms`);
          } else {
            toast.error('已保存但探测失败', res.probe.detail);
          }
          setApiKey('');
        },
        onError: (err) => toast.error('保存失败', errorMessage(err) + (errorHint(err) ? `：${errorHint(err)}` : ''))
      }
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>大模型接入</CardTitle>
        <CardDescription>
          红队 / 靶标 / 裁判 / 向量四角色模型路由。留空则走确定性离线回放，演示与 CI 不受影响。
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <Badge tone={online ? 'success' : data?.configured ? 'warning' : 'neutral'}>
            {online ? '已接入' : data?.configured ? '熔断降级中' : '离线回放'}
          </Badge>
          <span className="text-content-muted">供应商 {data?.provider || '未识别'}</span>
          <span className="font-mono text-content-faint">{data?.base_url || '未配置端点'}</span>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {(Object.entries(data?.models ?? {}) as [string, string][]).map(([role, model]) => (
            <div key={role} className="rounded-control border border-border bg-sunken px-3 py-2">
              <p className="text-[11px] text-content-faint">{role}</p>
              <p className="truncate font-mono text-xs text-content">{model || '（离线回放）'}</p>
            </div>
          ))}
        </div>

        {data?.last_error ? (
          <p className="rounded-control border border-warning/40 bg-warning/10 px-3 py-2 text-[11px] text-warning">
            最近一次失败：{data.last_error}
          </p>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-2">
          <Field label="供应商预设" id="llm-provider" hint="选择后自动填充端点与默认模型">
            <Select value={provider} onValueChange={setProvider}>
              <SelectTrigger id="llm-provider">
                <SelectValue placeholder="自定义 / 自动识别" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="custom">自定义（手动填端点）</SelectItem>
                {(providers.data ?? []).map((p) => (
                  <SelectItem key={p.name} value={p.name}>
                    {PROVIDER_LABEL[p.name] ?? p.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Field>
          <Field label="API Key" id="llm-key" hint="仅保存在服务进程内存，不落盘">
            <Input
              id="llm-key"
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={data?.api_key ? `当前：${data.api_key}` : 'sk-...'}
            />
          </Field>
          <Field label="端点 Base URL" id="llm-base" hint="OpenAI 兼容，缺省自动补 /v1">
            <Input
              id="llm-base"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder={data?.base_url || 'https://api.deepseek.com'}
            />
          </Field>
          <Field label="裁判模型" id="llm-judge" hint="判定攻击是否命中的模型">
            <Input
              id="llm-judge"
              value={judgeModel}
              onChange={(e) => setJudgeModel(e.target.value)}
              placeholder={data?.models.judge || 'deepseek-chat'}
            />
          </Field>
          <Field label="靶标模型" id="llm-target" hint="被攻击的 Agent 侧模型">
            <Input
              id="llm-target"
              value={targetModel}
              onChange={(e) => setTargetModel(e.target.value)}
              placeholder={data?.models.target || 'deepseek-chat'}
            />
          </Field>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button onClick={submit} loading={save.isPending}>
            保存并探测
          </Button>
          <Button
            variant="outline"
            loading={probe.isPending}
            onClick={() =>
              probe.mutate(undefined, {
                onSuccess: (res) =>
                  res.ok ? toast.success('端点可用', `${res.latency_ms}ms`) : toast.error('端点不可用', res.detail),
                onError: (err) => toast.error('探测失败', errorMessage(err))
              })
            }
          >
            仅探测连通性
          </Button>
          <span className="text-[11px] text-content-faint">
            成本账：{data?.tokens ?? 0} tokens / 在线调用 {data?.online_calls ?? 0} 次
          </span>
        </div>
      </CardContent>
    </Card>
  );
}