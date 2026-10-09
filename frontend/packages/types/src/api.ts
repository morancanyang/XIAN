/**
 * API 端点常量表：与 `services/api/xian_api/routers/*.py` 的 `@router.<verb>` 一一对应。
 * `pnpm codegen` 会重新导出 openapi.json，若路由发生变化请同步本表。
 */

export const API_PREFIX = '/api/v1';

export const ROUTES = {
  health: '/healthz',
  authLogin: '/api/v1/auth/login',
  authMe: '/api/v1/auth/me',

  agents: '/api/v1/agents',
  agent: (id: string) => `/api/v1/agents/${id}`,
  agentVerify: (id: string) => `/api/v1/agents/${id}/verify`,
  agentHealthcheck: (id: string) => `/api/v1/agents/${id}/healthcheck`,
  agentVersions: (id: string) => `/api/v1/agents/${id}/versions`,
  agentRecon: (id: string) => `/api/v1/agents/${id}/recon`,
  agentRecommendations: (id: string) => `/api/v1/agents/${id}/recommendations`,
  agentCredentials: (id: string) => `/api/v1/agents/${id}/credentials`,

  scenarios: '/api/v1/scenarios',
  scenario: (code: string) => `/api/v1/scenarios/${code}`,
  scenarioInstances: '/api/v1/scenarios/instances',
  scenarioInstance: (id: string) => `/api/v1/scenarios/instances/${id}`,
  scenarioInstanceCanaries: (id: string) => `/api/v1/scenarios/instances/${id}/canaries`,
  scenarioInstanceScan: (id: string) => `/api/v1/scenarios/instances/${id}/scan`,

  campaigns: '/api/v1/campaigns',
  campaign: (id: string) => `/api/v1/campaigns/${id}`,
  campaignPlan: (id: string) => `/api/v1/campaigns/${id}/plan`,
  campaignPlanPreview: '/api/v1/campaigns/preview-plan',
  campaignRun: (id: string) => `/api/v1/campaigns/${id}/run`,

  sessions: '/api/v1/sessions',
  session: (id: string) => `/api/v1/sessions/${id}`,
  sessionMessages: (id: string) => `/api/v1/sessions/${id}/messages`,
  sessionPause: (id: string) => `/api/v1/sessions/${id}/pause`,
  sessionComplete: (id: string) => `/api/v1/sessions/${id}/complete`,
  sessionArchive: (id: string) => `/api/v1/sessions/${id}/archive`,
  sessionCards: (id: string) => `/api/v1/sessions/${id}/cards`,

  campaignRecords: (id: string) => `/api/v1/campaigns/${id}/records`,
  record: (id: string) => `/api/v1/records/${id}`,
  recordTrace: (id: string) => `/api/v1/records/${id}/trace`,
  recordAdjudicate: (id: string) => `/api/v1/records/${id}/adjudicate`,

  reportByCampaign: (id: string) => `/api/v1/reports/campaigns/${id}`,
  reportByAgent: (id: string) => `/api/v1/reports/agents/${id}`,
  reports: '/api/v1/reports',
  report: (id: string) => `/api/v1/reports/${id}`,
  reportExport: (id: string) => `/api/v1/reports/${id}/export`,
  reportShare: (id: string) => `/api/v1/reports/${id}/share`,

  matrixCategories: '/api/v1/matrix/categories',
  matrixCoverage: '/api/v1/matrix/coverage',
  matrixFrameworks: '/api/v1/matrix/frameworks',
  matrixCases: '/api/v1/matrix/cases',
  matrixCase: (id: string) => `/api/v1/matrix/cases/${id}`,
  matrixOperators: '/api/v1/matrix/operators',
  matrixMutate: '/api/v1/matrix/mutate',
  matrixStrategies: '/api/v1/matrix/strategies',
  matrixStrategiesRender: '/api/v1/matrix/strategies/render',
  matrixCaseRender: (id: string) => `/api/v1/matrix/cases/${id}/render`,
  matrixCaseExport: (id: string) => `/api/v1/matrix/cases/${id}/export`,
  matrixCaseReview: (id: string) => `/api/v1/matrix/cases/${id}/review`,

  levels: '/api/v1/levels',
  levelProgress: '/api/v1/levels/progress',
  levelStart: (code: string) => `/api/v1/levels/${code}/start`,
  levelHint: (code: string) => `/api/v1/levels/${code}/hint`,
  levelSubmit: (code: string) => `/api/v1/levels/${code}/submit`,
  levelHardening: (code: string) => `/api/v1/levels/${code}/hardening`,
  profile: '/api/v1/profile',
  achievements: '/api/v1/profile/achievements',

  llmStatus: '/api/v1/llm/status',
  llmProviders: '/api/v1/llm/providers',
  llmProbe: '/api/v1/llm/probe',
  llmConfig: '/api/v1/llm/config',

  adminMembers: '/api/v1/admin/members',
  adminAuditLogs: '/api/v1/admin/audit-logs',
  adminGateRules: '/api/v1/admin/gate-rules',
  adminScanJobs: '/api/v1/admin/scan-jobs',
  adminGateEvaluate: '/api/v1/admin/gate/evaluate'
} as const;