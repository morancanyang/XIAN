-- ============================================================================
-- XIAN · AI Agent 红蓝对抗平台 —— PostgreSQL 全量建表脚本
-- 由 sql/schema_postgres.py 从 xian_core.db.models.Base.metadata 自动生成
-- 生成器：python sql/schema_postgres.py   （以确保 SQL 与 ORM 永远一致）
-- 兼容 PostgreSQL 16；仅依赖 gen_random_uuid() 与 CITEXT 之外的 PG 内建类型
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()


CREATE TABLE agents (
	name VARCHAR(128) NOT NULL, 
	access_type VARCHAR(16) NOT NULL, 
	endpoint TEXT NOT NULL, 
	description TEXT NOT NULL, 
	ownership_verified BOOLEAN NOT NULL, 
	ownership_method VARCHAR(32), 
	baseline_declaration JSONB NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_agents PRIMARY KEY (id)
);

CREATE INDEX ix_agents_tenant_id ON agents (tenant_id);
CREATE INDEX ix_agents_status ON agents (status);

CREATE TABLE agent_credentials (
	agent_id UUID NOT NULL, 
	token_encrypted TEXT NOT NULL, 
	scope VARCHAR(64) NOT NULL, 
	revoked BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	expires_at TIMESTAMP WITH TIME ZONE, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_agent_credentials PRIMARY KEY (id), 
	CONSTRAINT fk_agent_credentials_agent_id_agents FOREIGN KEY(agent_id) REFERENCES agents (id)
);

CREATE INDEX ix_agent_credentials_agent_id ON agent_credentials (agent_id);
CREATE INDEX ix_agent_credentials_tenant_id ON agent_credentials (tenant_id);

CREATE TABLE agent_versions (
	agent_id UUID NOT NULL, 
	prompt_hash VARCHAR(64) NOT NULL, 
	tools_snapshot JSONB NOT NULL, 
	model_config JSONB NOT NULL, 
	diff_summary JSONB NOT NULL, 
	source VARCHAR(16) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_agent_versions PRIMARY KEY (id), 
	CONSTRAINT fk_agent_versions_agent_id_agents FOREIGN KEY(agent_id) REFERENCES agents (id)
);

CREATE INDEX ix_agent_versions_agent_id ON agent_versions (agent_id);
CREATE INDEX ix_agent_versions_created_at ON agent_versions (created_at);

CREATE TABLE agent_profiles (
	agent_id UUID NOT NULL, 
	tools JSONB NOT NULL, 
	risk_levels JSONB NOT NULL, 
	refusal_boundary TEXT NOT NULL, 
	prompt_fragments JSONB NOT NULL, 
	fingerprint JSONB NOT NULL, 
	latency_p50 INTEGER NOT NULL, 
	latency_p99 INTEGER NOT NULL, 
	lang_prefs VARCHAR[] NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_agent_profiles PRIMARY KEY (id), 
	CONSTRAINT fk_agent_profiles_agent_id_agents FOREIGN KEY(agent_id) REFERENCES agents (id)
);

CREATE INDEX ix_agent_profiles_tenant_id ON agent_profiles (tenant_id);
CREATE INDEX ix_agent_profiles_agent_id ON agent_profiles (agent_id);

CREATE TABLE verification_records (
	agent_id UUID NOT NULL, 
	type VARCHAR(16) NOT NULL, 
	target VARCHAR(512) NOT NULL, 
	nonce VARCHAR(128) NOT NULL, 
	result VARCHAR(16) NOT NULL, 
	detail TEXT NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_verification_records PRIMARY KEY (id), 
	CONSTRAINT fk_verification_records_agent_id_agents FOREIGN KEY(agent_id) REFERENCES agents (id)
);

CREATE INDEX ix_verification_records_tenant_id ON verification_records (tenant_id);
CREATE INDEX ix_verification_records_agent_id ON verification_records (agent_id);

CREATE TABLE health_checks (
	agent_id UUID NOT NULL, 
	latency_ms INTEGER NOT NULL, 
	trace_sample JSONB NOT NULL, 
	result VARCHAR(32) NOT NULL, 
	detail TEXT NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_health_checks PRIMARY KEY (id), 
	CONSTRAINT fk_health_checks_agent_id_agents FOREIGN KEY(agent_id) REFERENCES agents (id)
);

CREATE INDEX ix_health_checks_tenant_id ON health_checks (tenant_id);
CREATE INDEX ix_health_checks_agent_id ON health_checks (agent_id);

CREATE TABLE change_signals (
	agent_id UUID NOT NULL, 
	kind VARCHAR(32) NOT NULL, 
	diff_preview JSONB NOT NULL, 
	handled BOOLEAN NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_change_signals PRIMARY KEY (id), 
	CONSTRAINT fk_change_signals_agent_id_agents FOREIGN KEY(agent_id) REFERENCES agents (id)
);

CREATE INDEX ix_change_signals_tenant_id ON change_signals (tenant_id);
CREATE INDEX ix_change_signals_agent_id ON change_signals (agent_id);

CREATE TABLE attack_records (
	agent_id UUID NOT NULL, 
	agent_version_id UUID, 
	campaign_id UUID, 
	session_id UUID, 
	case_id VARCHAR(64) NOT NULL, 
	category_code VARCHAR(16) NOT NULL, 
	strategy VARCHAR(64) NOT NULL, 
	mutation_ops JSONB NOT NULL, 
	turns INTEGER NOT NULL, 
	verdict VARCHAR(16) NOT NULL, 
	confidence FLOAT NOT NULL, 
	rule_hits JSONB NOT NULL, 
	evidence JSONB NOT NULL, 
	tokens INTEGER NOT NULL, 
	cost FLOAT NOT NULL, 
	trace_key VARCHAR(128) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_attack_records PRIMARY KEY (id)
);

CREATE INDEX ix_attack_records_verdict ON attack_records (verdict);
CREATE INDEX ix_attack_records_campaign_id ON attack_records (campaign_id);
CREATE INDEX ix_attack_records_category_code ON attack_records (category_code);
CREATE INDEX ix_attack_records_session_id ON attack_records (session_id);
CREATE INDEX ix_attack_records_tenant_id ON attack_records (tenant_id);
CREATE INDEX ix_attack_records_agent_version_id ON attack_records (agent_version_id);
CREATE INDEX ix_attack_records_agent_id ON attack_records (agent_id);
CREATE INDEX ix_attack_records_created_at ON attack_records (created_at);

CREATE TABLE verdicts (
	record_id UUID NOT NULL, 
	level VARCHAR(16) NOT NULL, 
	result VARCHAR(16) NOT NULL, 
	confidence FLOAT NOT NULL, 
	rule_hits JSONB NOT NULL, 
	evidence JSONB NOT NULL, 
	judge_model VARCHAR(128) NOT NULL, 
	reason TEXT NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_verdicts PRIMARY KEY (id), 
	CONSTRAINT fk_verdicts_record_id_attack_records FOREIGN KEY(record_id) REFERENCES attack_records (id) ON DELETE CASCADE
);

CREATE INDEX ix_verdicts_ts ON verdicts (ts);
CREATE INDEX ix_verdicts_record_id ON verdicts (record_id);

CREATE TABLE judge_calls (
	record_id UUID NOT NULL, 
	prompt_version VARCHAR(32) NOT NULL, 
	model VARCHAR(128) NOT NULL, 
	raw_output TEXT NOT NULL, 
	parsed JSONB NOT NULL, 
	latency_ms INTEGER NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_judge_calls PRIMARY KEY (id), 
	CONSTRAINT fk_judge_calls_record_id_attack_records FOREIGN KEY(record_id) REFERENCES attack_records (id) ON DELETE CASCADE
);

CREATE INDEX ix_judge_calls_record_id ON judge_calls (record_id);

CREATE TABLE judge_health (
	day VARCHAR(10) NOT NULL, 
	golden_ratio FLOAT NOT NULL, 
	agreement_rate FLOAT NOT NULL, 
	sample_audit_rate FLOAT NOT NULL, 
	total_records INTEGER NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_judge_health PRIMARY KEY (id), 
	CONSTRAINT uq_judge_health_day UNIQUE (day)
);


CREATE TABLE trace_events (
	subject_id UUID, 
	session_id UUID, 
	event_type VARCHAR(32) NOT NULL, 
	actor VARCHAR(16) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	canary_hit BOOLEAN NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_trace_events PRIMARY KEY (id)
);

CREATE INDEX ix_trace_events_session_id ON trace_events (session_id);
CREATE INDEX ix_trace_events_tenant_id ON trace_events (tenant_id);
CREATE INDEX ix_trace_events_event_type ON trace_events (event_type);
CREATE INDEX ix_trace_events_subject_id ON trace_events (subject_id);
CREATE INDEX ix_trace_events_ts ON trace_events (ts);

CREATE TABLE egress_logs (
	instance_id UUID, 
	mapped_domain VARCHAR(255) NOT NULL, 
	body_hash VARCHAR(64) NOT NULL, 
	canary_hit BOOLEAN NOT NULL, 
	allowed BOOLEAN NOT NULL, 
	detail JSONB NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_egress_logs PRIMARY KEY (id)
);

CREATE INDEX ix_egress_logs_ts ON egress_logs (ts);
CREATE INDEX ix_egress_logs_tenant_id ON egress_logs (tenant_id);
CREATE INDEX ix_egress_logs_instance_id ON egress_logs (instance_id);
CREATE INDEX ix_egress_logs_canary_hit ON egress_logs (canary_hit);

CREATE TABLE presets (
	code VARCHAR(32) NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	scope VARCHAR[] NOT NULL, 
	intensity VARCHAR(16) NOT NULL, 
	budget_default JSONB NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_presets PRIMARY KEY (id), 
	CONSTRAINT uq_presets_code UNIQUE (code)
);

CREATE INDEX ix_presets_tenant_id ON presets (tenant_id);

CREATE TABLE campaigns (
	agent_id UUID NOT NULL, 
	agent_version_id UUID, 
	scenario_instance_id UUID, 
	scope VARCHAR[] NOT NULL, 
	intensity VARCHAR(16) NOT NULL, 
	budget JSONB NOT NULL, 
	constraints JSONB NOT NULL, 
	judge_mode VARCHAR(16) NOT NULL, 
	output_mode VARCHAR(16) NOT NULL, 
	preset_id VARCHAR(32) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	sec_score INTEGER, 
	grade VARCHAR(1), 
	plan_dag JSONB NOT NULL, 
	progress INTEGER NOT NULL, 
	partial BOOLEAN NOT NULL, 
	created_by UUID, 
	started_at TIMESTAMP WITH TIME ZONE, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_campaigns PRIMARY KEY (id)
);

CREATE INDEX ix_campaigns_agent_version_id ON campaigns (agent_version_id);
CREATE INDEX ix_campaigns_tenant_id ON campaigns (tenant_id);
CREATE INDEX ix_campaigns_scenario_instance_id ON campaigns (scenario_instance_id);
CREATE INDEX ix_campaigns_status ON campaigns (status);
CREATE INDEX ix_campaigns_agent_id ON campaigns (agent_id);

CREATE TABLE campaign_runs (
	campaign_id UUID NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	progress INTEGER NOT NULL, 
	asr_live FLOAT NOT NULL, 
	tokens_used INTEGER NOT NULL, 
	budget_left INTEGER NOT NULL, 
	cases_done INTEGER NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	CONSTRAINT pk_campaign_runs PRIMARY KEY (id), 
	CONSTRAINT fk_campaign_runs_campaign_id_campaigns FOREIGN KEY(campaign_id) REFERENCES campaigns (id)
);

CREATE INDEX ix_campaign_runs_campaign_id ON campaign_runs (campaign_id);

CREATE TABLE strategy_runs (
	campaign_id UUID NOT NULL, 
	session_id UUID, 
	strategy_id VARCHAR(64) NOT NULL, 
	turns INTEGER NOT NULL, 
	escalations JSONB NOT NULL, 
	outcome VARCHAR(16) NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_strategy_runs PRIMARY KEY (id), 
	CONSTRAINT fk_strategy_runs_campaign_id_campaigns FOREIGN KEY(campaign_id) REFERENCES campaigns (id)
);

CREATE INDEX ix_strategy_runs_session_id ON strategy_runs (session_id);
CREATE INDEX ix_strategy_runs_campaign_id ON strategy_runs (campaign_id);

CREATE TABLE mutation_ops (
	name VARCHAR(64) NOT NULL, 
	type VARCHAR(32) NOT NULL, 
	semantics_safe BOOLEAN NOT NULL, 
	success_rate DOUBLE PRECISION NOT NULL, 
	description VARCHAR(255) NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_mutation_ops PRIMARY KEY (id), 
	CONSTRAINT uq_mutation_ops_name UNIQUE (name)
);


CREATE TABLE levels (
	code VARCHAR(16) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	scenario_code VARCHAR(16) NOT NULL, 
	goal VARCHAR(512) NOT NULL, 
	pass_criteria JSONB NOT NULL, 
	techniques VARCHAR[] NOT NULL, 
	h1 VARCHAR(512) NOT NULL, 
	h2 VARCHAR(512) NOT NULL, 
	h3 VARCHAR(1024) NOT NULL, 
	unlock_rule VARCHAR(128) NOT NULL, 
	difficulty VARCHAR(16) NOT NULL, 
	order_idx INTEGER NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_levels PRIMARY KEY (id)
);

CREATE INDEX ix_levels_tenant_id ON levels (tenant_id);
CREATE UNIQUE INDEX ix_levels_code ON levels (code);

CREATE TABLE level_progress (
	user_id UUID NOT NULL, 
	level_id VARCHAR(16) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	score INTEGER NOT NULL, 
	time_used INTEGER NOT NULL, 
	hints_used VARCHAR[] NOT NULL, 
	energy_left INTEGER NOT NULL, 
	attempts INTEGER NOT NULL, 
	dimension_coverage JSONB NOT NULL, 
	badge VARCHAR(64), 
	started_at TIMESTAMP WITH TIME ZONE, 
	completed_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	CONSTRAINT pk_level_progress PRIMARY KEY (id)
);

CREATE INDEX ix_level_progress_user_id ON level_progress (user_id);
CREATE INDEX ix_level_progress_level_id ON level_progress (level_id);

CREATE TABLE hint_usages (
	progress_id UUID NOT NULL, 
	level VARCHAR(4) NOT NULL, 
	energy_cost INTEGER NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_hint_usages PRIMARY KEY (id), 
	CONSTRAINT fk_hint_usages_progress_id_level_progress FOREIGN KEY(progress_id) REFERENCES level_progress (id) ON DELETE CASCADE
);

CREATE INDEX ix_hint_usages_progress_id ON hint_usages (progress_id);

CREATE TABLE achievements (
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	condition VARCHAR(512) NOT NULL, 
	rarity VARCHAR(16) NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_achievements PRIMARY KEY (id), 
	CONSTRAINT uq_achievements_code UNIQUE (code)
);


CREATE TABLE user_profiles (
	user_id UUID NOT NULL, 
	radar JSONB NOT NULL, 
	points INTEGER NOT NULL, 
	tier VARCHAR(16) NOT NULL, 
	badges VARCHAR[] NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	CONSTRAINT pk_user_profiles PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_user_profiles_user_id ON user_profiles (user_id);

CREATE TABLE ranks (
	user_id UUID NOT NULL, 
	tenant_id UUID, 
	points INTEGER NOT NULL, 
	tier VARCHAR(16) NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_ranks PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_ranks_user_id ON ranks (user_id);

CREATE TABLE hardening_options (
	code VARCHAR(64) NOT NULL, 
	level_id VARCHAR(16) NOT NULL, 
	type VARCHAR(16) NOT NULL, 
	diff_preview JSONB NOT NULL, 
	expected_effect VARCHAR(512) NOT NULL, 
	side_effects VARCHAR(512) NOT NULL, 
	applied_by_default BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_hardening_options PRIMARY KEY (id), 
	CONSTRAINT uq_hardening_options_code UNIQUE (code)
);


CREATE TABLE attack_categories (
	code VARCHAR(16) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	stage VARCHAR(64) NOT NULL, 
	attack_surface VARCHAR(64) NOT NULL, 
	difficulty VARCHAR(16) NOT NULL, 
	impact VARCHAR(16) NOT NULL, 
	techniques VARCHAR[] NOT NULL, 
	detection_signals VARCHAR[] NOT NULL, 
	owasp_ref VARCHAR[] NOT NULL, 
	atlas_ref VARCHAR[] NOT NULL, 
	description TEXT NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_attack_categories PRIMARY KEY (id)
);

CREATE INDEX ix_attack_categories_tenant_id ON attack_categories (tenant_id);
CREATE UNIQUE INDEX ix_attack_categories_code ON attack_categories (code);

CREATE TABLE framework_mappings (
	framework VARCHAR(32) NOT NULL, 
	clause VARCHAR(128) NOT NULL, 
	category_ids VARCHAR[] NOT NULL, 
	coverage VARCHAR(32) NOT NULL, 
	note VARCHAR(255) NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_framework_mappings PRIMARY KEY (id)
);

CREATE INDEX ix_framework_mappings_framework ON framework_mappings (framework);

CREATE TABLE attack_cases (
	case_id VARCHAR(64) NOT NULL, 
	category_code VARCHAR(16) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	payload_template TEXT NOT NULL, 
	variables VARCHAR[] NOT NULL, 
	scenario_tags VARCHAR[] NOT NULL, 
	difficulty VARCHAR(16) NOT NULL, 
	success_criteria JSONB NOT NULL, 
	judge_prompt TEXT NOT NULL, 
	severity VARCHAR(16) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	version INTEGER NOT NULL, 
	contributor VARCHAR(128) NOT NULL, 
	success_rate DOUBLE PRECISION NOT NULL, 
	usage_count INTEGER NOT NULL, 
	export_allowed BOOLEAN NOT NULL, 
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_attack_cases PRIMARY KEY (id)
);

CREATE INDEX ix_attack_cases_tenant_id ON attack_cases (tenant_id);
CREATE INDEX ix_attack_cases_category_code ON attack_cases (category_code);
CREATE INDEX ix_attack_cases_status ON attack_cases (status);
CREATE UNIQUE INDEX ix_attack_cases_case_id ON attack_cases (case_id);

CREATE TABLE case_reviews (
	case_id VARCHAR(64) NOT NULL, 
	reviewer UUID, 
	result VARCHAR(16) NOT NULL, 
	comment TEXT NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_case_reviews PRIMARY KEY (id)
);

CREATE INDEX ix_case_reviews_case_id ON case_reviews (case_id);

CREATE TABLE contributions (
	author UUID, 
	case_id VARCHAR(64) NOT NULL, 
	pipeline_status VARCHAR(32) NOT NULL, 
	points INTEGER NOT NULL, 
	auto_test_result JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_contributions PRIMARY KEY (id)
);

CREATE INDEX ix_contributions_author ON contributions (author);

CREATE TABLE root_causes (
	code VARCHAR(64) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	category VARCHAR(64) NOT NULL, 
	fix_playbook_ref VARCHAR(64) NOT NULL, 
	description TEXT NOT NULL, 
	match_signals JSONB NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_root_causes PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_root_causes_code ON root_causes (code);

CREATE TABLE playbooks (
	code VARCHAR(64) NOT NULL, 
	root_cause_code VARCHAR(64) NOT NULL, 
	artifacts JSONB NOT NULL, 
	min_version VARCHAR(16) NOT NULL, 
	expected_effect VARCHAR(512) NOT NULL, 
	side_effects VARCHAR(512) NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_playbooks PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_playbooks_code ON playbooks (code);
CREATE INDEX ix_playbooks_root_cause_code ON playbooks (root_cause_code);

CREATE TABLE findings (
	campaign_id UUID, 
	session_id UUID, 
	record_ids VARCHAR[] NOT NULL, 
	root_cause_code VARCHAR(64) NOT NULL, 
	severity VARCHAR(16) NOT NULL, 
	affected_config JSONB NOT NULL, 
	impact TEXT NOT NULL, 
	trace_refs VARCHAR[] NOT NULL, 
	evidence JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_findings PRIMARY KEY (id)
);

CREATE INDEX ix_findings_campaign_id ON findings (campaign_id);
CREATE INDEX ix_findings_session_id ON findings (session_id);
CREATE INDEX ix_findings_root_cause_code ON findings (root_cause_code);
CREATE INDEX ix_findings_tenant_id ON findings (tenant_id);

CREATE TABLE attack_paths (
	campaign_id UUID, 
	session_id UUID, 
	nodes JSONB NOT NULL, 
	edges JSONB NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_attack_paths PRIMARY KEY (id)
);

CREATE INDEX ix_attack_paths_session_id ON attack_paths (session_id);
CREATE INDEX ix_attack_paths_campaign_id ON attack_paths (campaign_id);

CREATE TABLE recommendations (
	finding_id UUID NOT NULL, 
	type VARCHAR(32) NOT NULL, 
	priority VARCHAR(4) NOT NULL, 
	effort VARCHAR(16) NOT NULL, 
	diff_payload JSONB NOT NULL, 
	playbook_ref VARCHAR(64) NOT NULL, 
	expected_effect VARCHAR(512) NOT NULL, 
	side_effects VARCHAR(512) NOT NULL, 
	applied BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_recommendations PRIMARY KEY (id), 
	CONSTRAINT fk_recommendations_finding_id_findings FOREIGN KEY(finding_id) REFERENCES findings (id) ON DELETE CASCADE
);

CREATE INDEX ix_recommendations_finding_id ON recommendations (finding_id);

CREATE TABLE remediation_runs (
	recommendation_id UUID NOT NULL, 
	campaign_id UUID, 
	before_sec_score INTEGER NOT NULL, 
	after_sec_score INTEGER NOT NULL, 
	before_asr FLOAT NOT NULL, 
	after_asr FLOAT NOT NULL, 
	regression_pass_rate FLOAT NOT NULL, 
	replayed_record_ids VARCHAR[] NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	reverted BOOLEAN NOT NULL, 
	applied_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	CONSTRAINT pk_remediation_runs PRIMARY KEY (id), 
	CONSTRAINT fk_remediation_runs_recommendation_id_recommendations FOREIGN KEY(recommendation_id) REFERENCES recommendations (id) ON DELETE CASCADE
);

CREATE INDEX ix_remediation_runs_recommendation_id ON remediation_runs (recommendation_id);
CREATE INDEX ix_remediation_runs_campaign_id ON remediation_runs (campaign_id);

CREATE TABLE reports (
	subject_type VARCHAR(16) NOT NULL, 
	subject_id UUID NOT NULL, 
	version INTEGER NOT NULL, 
	sec_score INTEGER NOT NULL, 
	grade VARCHAR(1) NOT NULL, 
	chapters JSONB NOT NULL, 
	object_keys JSONB NOT NULL, 
	share JSONB NOT NULL, 
	partial BOOLEAN NOT NULL, 
	coverage_pct DOUBLE PRECISION NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_reports PRIMARY KEY (id)
);

CREATE INDEX ix_reports_subject_id ON reports (subject_id);
CREATE INDEX ix_reports_created_at ON reports (created_at);
CREATE INDEX ix_reports_tenant_id ON reports (tenant_id);

CREATE TABLE report_exports (
	report_id UUID NOT NULL, 
	format VARCHAR(16) NOT NULL, 
	desensitize_level VARCHAR(16) NOT NULL, 
	file_ref VARCHAR(512) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_report_exports PRIMARY KEY (id), 
	CONSTRAINT fk_report_exports_report_id_reports FOREIGN KEY(report_id) REFERENCES reports (id) ON DELETE CASCADE
);

CREATE INDEX ix_report_exports_report_id ON report_exports (report_id);

CREATE TABLE subscriptions (
	user_id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	cadence VARCHAR(16) NOT NULL, 
	channels VARCHAR[] NOT NULL, 
	recipients VARCHAR[] NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_subscriptions PRIMARY KEY (id)
);

CREATE INDEX ix_subscriptions_user_id ON subscriptions (user_id);
CREATE INDEX ix_subscriptions_tenant_id ON subscriptions (tenant_id);

CREATE TABLE notifications (
	tenant_id UUID, 
	user_id UUID, 
	type VARCHAR(32) NOT NULL, 
	channel VARCHAR(16) NOT NULL, 
	payload JSONB NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	retries INTEGER NOT NULL, 
	error TEXT NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_notifications PRIMARY KEY (id)
);

CREATE INDEX ix_notifications_tenant_id ON notifications (tenant_id);
CREATE INDEX ix_notifications_ts ON notifications (ts);
CREATE INDEX ix_notifications_user_id ON notifications (user_id);

CREATE TABLE alerts (
	campaign_id UUID, 
	session_id UUID, 
	record_id UUID, 
	severity VARCHAR(16) NOT NULL, 
	channels VARCHAR[] NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	message TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_alerts PRIMARY KEY (id)
);

CREATE INDEX ix_alerts_created_at ON alerts (created_at);
CREATE INDEX ix_alerts_tenant_id ON alerts (tenant_id);
CREATE INDEX ix_alerts_campaign_id ON alerts (campaign_id);
CREATE INDEX ix_alerts_session_id ON alerts (session_id);

CREATE TABLE gate_rules (
	max_score_drop INTEGER NOT NULL, 
	block_on_severity VARCHAR(16) NOT NULL, 
	enabled BOOLEAN NOT NULL, 
	webhook_url VARCHAR(512) NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_gate_rules PRIMARY KEY (id)
);

CREATE INDEX ix_gate_rules_tenant_id ON gate_rules (tenant_id);

CREATE TABLE scan_jobs (
	agent_id UUID NOT NULL, 
	agent_version_id UUID, 
	campaign_id UUID, 
	trigger VARCHAR(16) NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	verdict VARCHAR(16), 
	exit_code INTEGER, 
	ci_context JSONB NOT NULL, 
	pipeline_url VARCHAR(512) NOT NULL, 
	message TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_scan_jobs PRIMARY KEY (id)
);

CREATE INDEX ix_scan_jobs_agent_version_id ON scan_jobs (agent_version_id);
CREATE INDEX ix_scan_jobs_created_at ON scan_jobs (created_at);
CREATE INDEX ix_scan_jobs_campaign_id ON scan_jobs (campaign_id);
CREATE INDEX ix_scan_jobs_tenant_id ON scan_jobs (tenant_id);
CREATE INDEX ix_scan_jobs_agent_id ON scan_jobs (agent_id);
CREATE INDEX ix_scan_jobs_status ON scan_jobs (status);

CREATE TABLE scenarios (
	code VARCHAR(16) NOT NULL, 
	name VARCHAR(128) NOT NULL, 
	category VARCHAR(64) NOT NULL, 
	env_template JSONB NOT NULL, 
	script VARCHAR[] NOT NULL, 
	default_difficulty VARCHAR(16) NOT NULL, 
	monitors VARCHAR[] NOT NULL, 
	description TEXT NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_scenarios PRIMARY KEY (id)
);

CREATE UNIQUE INDEX ix_scenarios_code ON scenarios (code);
CREATE INDEX ix_scenarios_tenant_id ON scenarios (tenant_id);

CREATE TABLE scenario_tools (
	scenario_id UUID NOT NULL, 
	name VARCHAR(64) NOT NULL, 
	scope VARCHAR(16) NOT NULL, 
	risk_level VARCHAR(16) NOT NULL, 
	require_confirm BOOLEAN NOT NULL, 
	description TEXT NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_scenario_tools PRIMARY KEY (id), 
	CONSTRAINT fk_scenario_tools_scenario_id_scenarios FOREIGN KEY(scenario_id) REFERENCES scenarios (id)
);

CREATE INDEX ix_scenario_tools_scenario_id ON scenario_tools (scenario_id);

CREATE TABLE scenario_canaries (
	scenario_id UUID NOT NULL, 
	instance_id UUID, 
	type VARCHAR(16) NOT NULL, 
	value VARCHAR(255) NOT NULL, 
	plant_location VARCHAR[] NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_scenario_canaries PRIMARY KEY (id), 
	CONSTRAINT fk_scenario_canaries_scenario_id_scenarios FOREIGN KEY(scenario_id) REFERENCES scenarios (id)
);

CREATE INDEX ix_scenario_canaries_instance_id ON scenario_canaries (instance_id);
CREATE INDEX ix_scenario_canaries_tenant_id ON scenario_canaries (tenant_id);
CREATE INDEX ix_scenario_canaries_scenario_id ON scenario_canaries (scenario_id);

CREATE TABLE scenario_instances (
	scenario_id UUID NOT NULL, 
	seed_data_snapshot JSONB NOT NULL, 
	data_scale INTEGER NOT NULL, 
	language VARCHAR(16) NOT NULL, 
	canary_enhanced BOOLEAN NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	compose_project VARCHAR(128) NOT NULL, 
	baseline_pass_rate DOUBLE PRECISION NOT NULL, 
	expired_at TIMESTAMP WITH TIME ZONE, 
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_scenario_instances PRIMARY KEY (id), 
	CONSTRAINT fk_scenario_instances_scenario_id_scenarios FOREIGN KEY(scenario_id) REFERENCES scenarios (id)
);

CREATE INDEX ix_scenario_instances_scenario_id ON scenario_instances (scenario_id);
CREATE INDEX ix_scenario_instances_tenant_id ON scenario_instances (tenant_id);
CREATE INDEX ix_scenario_instances_status ON scenario_instances (status);

CREATE TABLE canary_hits (
	canary_id UUID NOT NULL, 
	instance_id UUID, 
	campaign_id UUID, 
	session_id UUID, 
	via VARCHAR(16) NOT NULL, 
	trace_ref VARCHAR(255) NOT NULL, 
	detail JSONB NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_canary_hits PRIMARY KEY (id), 
	CONSTRAINT fk_canary_hits_canary_id_scenario_canaries FOREIGN KEY(canary_id) REFERENCES scenario_canaries (id)
);

CREATE INDEX ix_canary_hits_tenant_id ON canary_hits (tenant_id);
CREATE INDEX ix_canary_hits_instance_id ON canary_hits (instance_id);
CREATE INDEX ix_canary_hits_session_id ON canary_hits (session_id);
CREATE INDEX ix_canary_hits_canary_id ON canary_hits (canary_id);
CREATE INDEX ix_canary_hits_campaign_id ON canary_hits (campaign_id);

CREATE TABLE seed_datasets (
	scenario_id UUID NOT NULL, 
	rules JSONB NOT NULL, 
	snapshot_ref VARCHAR(255) NOT NULL, 
	generator_version VARCHAR(32) NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_seed_datasets PRIMARY KEY (id), 
	CONSTRAINT fk_seed_datasets_scenario_id_scenarios FOREIGN KEY(scenario_id) REFERENCES scenarios (id)
);

CREATE INDEX ix_seed_datasets_scenario_id ON seed_datasets (scenario_id);
CREATE INDEX ix_seed_datasets_tenant_id ON seed_datasets (tenant_id);

CREATE TABLE custom_scenarios (
	name VARCHAR(128) NOT NULL, 
	dsl_version VARCHAR(16) NOT NULL, 
	env_ref VARCHAR(255) NOT NULL, 
	tools JSONB NOT NULL, 
	canaries JSONB NOT NULL, 
	monitors VARCHAR[] NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	id UUID NOT NULL, 
	tenant_id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_custom_scenarios PRIMARY KEY (id)
);

CREATE INDEX ix_custom_scenarios_tenant_id ON custom_scenarios (tenant_id);

CREATE TABLE scores (
	subject_type VARCHAR(16) NOT NULL, 
	subject_id UUID NOT NULL, 
	sec_score INTEGER NOT NULL, 
	grade VARCHAR(1) NOT NULL, 
	dimension_scores JSONB NOT NULL, 
	category_asr JSONB NOT NULL, 
	percentile FLOAT, 
	segment VARCHAR(64) NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_scores PRIMARY KEY (id)
);

CREATE INDEX ix_scores_tenant_id ON scores (tenant_id);
CREATE INDEX ix_scores_subject_id ON scores (subject_id);
CREATE INDEX ix_scores_computed_at ON scores (computed_at);

CREATE TABLE benchmarks (
	segment VARCHAR(64) NOT NULL, 
	sample_size INTEGER NOT NULL, 
	mean FLOAT NOT NULL, 
	percentiles JSONB NOT NULL, 
	common_weak_points JSONB NOT NULL, 
	computed_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_benchmarks PRIMARY KEY (id)
);

CREATE INDEX ix_benchmarks_segment ON benchmarks (segment);

CREATE TABLE trend_points (
	agent_id UUID NOT NULL, 
	version_id UUID, 
	campaign_id UUID, 
	sec_score INTEGER NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_trend_points PRIMARY KEY (id)
);

CREATE INDEX ix_trend_points_ts ON trend_points (ts);
CREATE INDEX ix_trend_points_version_id ON trend_points (version_id);
CREATE INDEX ix_trend_points_agent_id ON trend_points (agent_id);

CREATE TABLE sessions (
	id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	agent_id UUID NOT NULL, 
	scenario_instance_id UUID, 
	level_id VARCHAR(16), 
	mode VARCHAR(16) NOT NULL, 
	goal TEXT NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	tokens_used INTEGER NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	CONSTRAINT pk_sessions PRIMARY KEY (id)
);

CREATE INDEX ix_sessions_tenant_id ON sessions (tenant_id);
CREATE INDEX ix_sessions_user_id ON sessions (user_id);
CREATE INDEX ix_sessions_status ON sessions (status);
CREATE INDEX ix_sessions_mode ON sessions (mode);
CREATE INDEX ix_sessions_scenario_instance_id ON sessions (scenario_instance_id);
CREATE INDEX ix_sessions_agent_id ON sessions (agent_id);

CREATE TABLE session_messages (
	session_id UUID NOT NULL, 
	role VARCHAR(16) NOT NULL, 
	content TEXT NOT NULL, 
	payload_ref VARCHAR(255) NOT NULL, 
	trace_ref VARCHAR(255) NOT NULL, 
	verdict VARCHAR(16), 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_session_messages PRIMARY KEY (id), 
	CONSTRAINT fk_session_messages_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

CREATE INDEX ix_session_messages_ts ON session_messages (ts);
CREATE INDEX ix_session_messages_session_id ON session_messages (session_id);

CREATE TABLE battle_cards (
	session_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	category_id VARCHAR(16) NOT NULL, 
	severity VARCHAR(16) NOT NULL, 
	evidence JSONB NOT NULL, 
	payload TEXT NOT NULL, 
	record_id UUID, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_battle_cards PRIMARY KEY (id), 
	CONSTRAINT fk_battle_cards_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE
);

CREATE INDEX ix_battle_cards_user_id ON battle_cards (user_id);
CREATE INDEX ix_battle_cards_session_id ON battle_cards (session_id);
CREATE INDEX ix_battle_cards_created_at ON battle_cards (created_at);

CREATE TABLE tenants (
	name VARCHAR(128) NOT NULL, 
	plan VARCHAR(32) NOT NULL, 
	quota JSONB NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_tenants PRIMARY KEY (id)
);


CREATE TABLE users (
	name VARCHAR(128) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_users PRIMARY KEY (id), 
	CONSTRAINT uq_users_email UNIQUE (email)
);


CREATE TABLE members (
	tenant_id UUID NOT NULL, 
	user_id UUID NOT NULL, 
	role VARCHAR(32) NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	id UUID NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	CONSTRAINT pk_members PRIMARY KEY (id), 
	CONSTRAINT uq_member_tenant_user UNIQUE (tenant_id, user_id), 
	CONSTRAINT fk_members_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id), 
	CONSTRAINT fk_members_user_id_users FOREIGN KEY(user_id) REFERENCES users (id)
);

CREATE INDEX ix_members_user_id ON members (user_id);
CREATE INDEX ix_members_tenant_id ON members (tenant_id);

CREATE TABLE tenant_features (
	tenant_id UUID NOT NULL, 
	flag VARCHAR(64) NOT NULL, 
	rollout INTEGER NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_tenant_features PRIMARY KEY (id), 
	CONSTRAINT uq_tenant_feature UNIQUE (tenant_id, flag), 
	CONSTRAINT fk_tenant_features_tenant_id_tenants FOREIGN KEY(tenant_id) REFERENCES tenants (id)
);

CREATE INDEX ix_tenant_features_tenant_id ON tenant_features (tenant_id);

CREATE TABLE quota_usages (
	metric VARCHAR(64) NOT NULL, 
	used INTEGER NOT NULL, 
	"window" VARCHAR(32) NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_quota_usages PRIMARY KEY (id)
);

CREATE INDEX ix_quota_usages_tenant_id ON quota_usages (tenant_id);

CREATE TABLE audit_logs (
	tenant_id UUID, 
	user_id UUID, 
	action VARCHAR(128) NOT NULL, 
	target VARCHAR(255) NOT NULL, 
	result VARCHAR(32) NOT NULL, 
	ip VARCHAR(64) NOT NULL, 
	detail JSONB NOT NULL, 
	ts TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_audit_logs PRIMARY KEY (id)
);

CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);
CREATE INDEX ix_audit_logs_action ON audit_logs (action);
CREATE INDEX ix_audit_logs_tenant_id ON audit_logs (tenant_id);
CREATE INDEX ix_audit_logs_ts ON audit_logs (ts);

CREATE TABLE abuse_events (
	type VARCHAR(64) NOT NULL, 
	severity VARCHAR(16) NOT NULL, 
	evidence JSONB NOT NULL, 
	status VARCHAR(16) NOT NULL, 
	handled_by UUID, 
	note TEXT NOT NULL, 
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
	tenant_id UUID NOT NULL, 
	id UUID NOT NULL, 
	CONSTRAINT pk_abuse_events PRIMARY KEY (id)
);

CREATE INDEX ix_abuse_events_tenant_id ON abuse_events (tenant_id);
