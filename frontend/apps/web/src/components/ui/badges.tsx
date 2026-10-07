import { Badge, type BadgeTone } from '@xian/ui';
import { AGENT_STATUS_LABEL, CAMPAIGN_STATUS_LABEL, VERDICT_LABEL, SEVERITY_LABEL } from '@xian/types';
import type { AgentStatus, CampaignStatus, Severity, Verdict } from '@xian/types';

const AGENT_TONE: Record<AgentStatus, BadgeTone> = {
  unverified: 'warning',
  active: 'success',
  testing: 'blue',
  offline: 'neutral',
  archived: 'neutral'
};

const CAMPAIGN_TONE: Record<CampaignStatus, BadgeTone> = {
  draft: 'neutral',
  scheduled: 'neutral',
  preparing: 'coach',
  attacking: 'red',
  analyzing: 'coach',
  reporting: 'coach',
  completed: 'success',
  cancelled: 'neutral',
  tripped: 'danger',
  env_failed: 'danger',
  failed: 'danger'
};

const VERDICT_TONE: Record<Verdict, BadgeTone> = {
  success: 'danger',
  partial: 'warning',
  fail: 'success',
  unavailable: 'neutral'
};

const SEVERITY_TONE: Record<Severity, BadgeTone> = {
  critical: 'danger',
  high: 'danger',
  medium: 'warning',
  low: 'neutral'
};

export const AgentStatusBadge = ({ status }: { status: AgentStatus }) => (
  <Badge tone={AGENT_TONE[status]}>{AGENT_STATUS_LABEL[status]}</Badge>
);

export const CampaignStatusBadge = ({ status }: { status: CampaignStatus }) => (
  <Badge tone={CAMPAIGN_TONE[status]}>{CAMPAIGN_STATUS_LABEL[status]}</Badge>
);

const GRADE_TONE: Record<string, BadgeTone> = {
  S: 'success',
  A: 'success',
  B: 'blue',
  C: 'warning',
  D: 'danger'
};

export const GradeBadge = ({ grade }: { grade: string | null }) =>
  grade ? (
    <Badge tone={GRADE_TONE[grade] ?? 'neutral'}>{grade}</Badge>
  ) : (
    <span className="text-xs text-content-faint">—</span>
  );

export const VerdictBadge = ({ verdict, className }: { verdict: Verdict; className?: string }) => (
  <Badge tone={VERDICT_TONE[verdict]} className={className}>
    {VERDICT_LABEL[verdict]}
  </Badge>
);

export const SeverityBadge = ({ severity }: { severity: Severity }) => (
  <Badge tone={SEVERITY_TONE[severity]}>{SEVERITY_LABEL[severity]}</Badge>
);