"""各领域仓储：services 只允许通过这些类访问 PostgreSQL。"""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: F401  # 对外复出的依赖基类  # 对外复出的依赖基类

from ...errors import NotFoundError
from ..models import (
    Agent,
    AgentCredential,
    AgentProfile,
    AgentVersion,
    Alert,
    AttackCase,
    AttackCategory,
    AttackRecord,
    AuditLog,
    BattleCard,
    Campaign,
    CampaignRun,
    CanaryHit,
    ChangeSignal,
    EgressLog,
    Finding,
    GateRule,
    HealthCheck,
    JudgeCall,
    Level,
    LevelProgress,
    Member,
    Notification,
    Preset,
    Recommendation,
    RemediationRun,
    Report,
    ReportExport,
    ScanJob,
    Scenario,
    ScenarioCanary,
    ScenarioInstance,
    Score,
    Session,
    SessionMessage,
    Subscription,
    Tenant,
    TraceEvent,
    User,
    Verdict,
    VerificationRecord,
)
from .base import Repository

_REPO_CACHE: dict[tuple[type, tuple[str, ...]], type[Repository]] = {}


def repo_for(model: type) -> type[Repository]:
    """惰性生成轻量仓储类，避免为每个实体手写样板代码。"""
    key = (model, ())
    if key not in _REPO_CACHE:
        _REPO_CACHE[key] = type(f"{model.__name__}Repository", (Repository,), {"model": model})
    return _REPO_CACHE[key]


class TenantRepository(Repository[Tenant]):
    model = Tenant


class UserRepository(Repository[User]):
    model = User

    async def get_by_email(self, email: str) -> User:
        stmt = select(User).where(User.email == email)
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            raise NotFoundError(f"用户 {email} 不存在")
        return row


class MemberRepository(Repository[Member]):
    model = Member

    async def role_of(self, tenant_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
        stmt = select(Member.role).where(
            Member.tenant_id == tenant_id, Member.user_id == user_id, Member.status == "active"
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class AuditRepository(Repository[AuditLog]):
    model = AuditLog

    async def record(
        self,
        *,
        action: str,
        target: str = "",
        result: str = "success",
        ip: str = "",
        tenant_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        detail: dict | None = None,
    ) -> AuditLog:
        return await self.add(
            AuditLog(
                tenant_id=tenant_id,
                user_id=user_id,
                action=action,
                target=target,
                result=result,
                ip=ip,
                detail=detail or {},
            )
        )


class AgentRepository(Repository[Agent]):
    model = Agent

    async def active_for_tenant(self) -> Sequence[Agent]:
        stmt = self._base_query().where(Agent.status == "active").order_by(Agent.created_at.desc())
        return (await self.session.execute(stmt)).scalars().all()


class AgentVersionRepository(Repository[AgentVersion]):
    model = AgentVersion

    async def latest(self, agent_id: uuid.UUID) -> AgentVersion | None:
        stmt = (
            select(AgentVersion)
            .where(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_for_agent(self, agent_id: uuid.UUID) -> Sequence[AgentVersion]:
        stmt = (
            select(AgentVersion)
            .where(AgentVersion.agent_id == agent_id)
            .order_by(AgentVersion.created_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().all()


class AgentProfileRepository(Repository[AgentProfile]):
    model = AgentProfile

    async def latest(self, agent_id: uuid.UUID) -> AgentProfile | None:
        stmt = (
            select(AgentProfile)
            .where(AgentProfile.agent_id == agent_id)
            .order_by(AgentProfile.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class ScenarioRepository(Repository[Scenario]):
    model = Scenario


class ScenarioInstanceRepository(Repository[ScenarioInstance]):
    model = ScenarioInstance

    async def expire_due(self) -> Sequence[ScenarioInstance]:
        stmt = select(ScenarioInstance).where(
            ScenarioInstance.status == "ready",
            ScenarioInstance.expired_at.is_not(None),
            ScenarioInstance.expired_at < datetime.now().astimezone(),
        )
        return (await self.session.execute(stmt)).scalars().all()


class ScenarioCanaryRepository(Repository[ScenarioCanary]):
    model = ScenarioCanary

    async def for_instance(self, instance_id: uuid.UUID) -> Sequence[ScenarioCanary]:
        stmt = self._base_query().where(ScenarioCanary.instance_id == instance_id)
        return (await self.session.execute(stmt)).scalars().all()


class CanaryHitRepository(Repository[CanaryHit]):
    model = CanaryHit


class CampaignRepository(Repository[Campaign]):
    model = Campaign

    async def update_status(self, campaign_id: uuid.UUID, status: str, **fields) -> Campaign:
        campaign = await self.get(campaign_id)
        campaign.status = status
        for key, value in fields.items():
            setattr(campaign, key, value)
        await self.session.flush()
        return campaign


class CampaignRunRepository(Repository[CampaignRun]):
    model = CampaignRun

    async def for_campaign(self, campaign_id: uuid.UUID) -> CampaignRun:
        stmt = select(CampaignRun).where(CampaignRun.campaign_id == campaign_id)
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = await self.add(CampaignRun(campaign_id=campaign_id))
        return row


class AttackRecordRepository(Repository[AttackRecord]):
    model = AttackRecord

    async def for_campaign(self, campaign_id: uuid.UUID) -> Sequence[AttackRecord]:
        stmt = self._base_query().where(AttackRecord.campaign_id == campaign_id)
        return (await self.session.execute(stmt)).scalars().all()

    async def for_session(self, session_id: uuid.UUID) -> Sequence[AttackRecord]:
        stmt = self._base_query().where(AttackRecord.session_id == session_id)
        return (await self.session.execute(stmt)).scalars().all()

    async def for_agent(self, agent_id: uuid.UUID, limit: int = 500) -> Sequence[AttackRecord]:
        stmt = (
            self._base_query()
            .where(AttackRecord.agent_id == agent_id)
            .order_by(AttackRecord.created_at.desc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()


class SessionRepository(Repository[Session]):
    model = Session

    async def stale(self, minutes: int = 30) -> Sequence[Session]:
        cutoff = datetime.now().astimezone() - timedelta(minutes=minutes)
        stmt = select(Session).where(Session.status == "active", Session.last_activity_at < cutoff)
        return (await self.session.execute(stmt)).scalars().all()


class SessionMessageRepository(Repository[SessionMessage]):
    model = SessionMessage

    async def for_session(self, session_id: uuid.UUID, limit: int = 200) -> Sequence[SessionMessage]:
        stmt = (
            select(SessionMessage)
            .where(SessionMessage.session_id == session_id)
            .order_by(SessionMessage.ts.asc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def recent(self, session_id: uuid.UUID, limit: int = 50) -> Sequence[SessionMessage]:
        """最近 limit 条消息，按时间正序返回（倒序取窗口再反转，保证窗口永远是最新的）。"""
        stmt = (
            select(SessionMessage)
            .where(SessionMessage.session_id == session_id)
            .order_by(SessionMessage.ts.desc())
            .limit(limit)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(reversed(rows))


class BattleCardRepository(Repository[BattleCard]):
    model = BattleCard

    async def for_user(self, user_id: uuid.UUID) -> Sequence[BattleCard]:
        stmt = (
            select(BattleCard)
            .where(BattleCard.user_id == user_id)
            .order_by(BattleCard.created_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def for_session(self, session_id: uuid.UUID) -> Sequence[BattleCard]:
        """按会话取战斗卡片：接口本身带了 session_id，不该回全局列表。"""
        stmt = (
            select(BattleCard)
            .where(BattleCard.session_id == session_id)
            .order_by(BattleCard.created_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().all()


class LevelRepository(Repository[Level]):
    model = Level

    async def by_code(self, code: str) -> Level | None:
        stmt = select(Level).where(Level.code == code)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def all_ordered(self) -> Sequence[Level]:
        stmt = select(Level).order_by(Level.order_idx.asc())
        return (await self.session.execute(stmt)).scalars().all()


class LevelProgressRepository(Repository[LevelProgress]):
    model = LevelProgress

    async def for_user(self, user_id: uuid.UUID) -> Sequence[LevelProgress]:
        stmt = select(LevelProgress).where(LevelProgress.user_id == user_id)
        return (await self.session.execute(stmt)).scalars().all()

    async def get_for_user_level(self, user_id: uuid.UUID, level_id: str) -> LevelProgress | None:
        stmt = select(LevelProgress).where(
            LevelProgress.user_id == user_id, LevelProgress.level_id == level_id
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()


class AttackCategoryRepository(Repository[AttackCategory]):
    model = AttackCategory

    async def by_code(self, code: str) -> AttackCategory | None:
        stmt = select(AttackCategory).where(AttackCategory.code == code)
        return (await self.session.execute(stmt)).scalar_one_or_none()


class AttackCaseRepository(Repository[AttackCase]):
    model = AttackCase

    async def by_category(self, code: str) -> Sequence[AttackCase]:
        stmt = self._base_query().where(
            AttackCase.category_code == code, AttackCase.status == "published"
        )
        return (await self.session.execute(stmt)).scalars().all()


class FindingRepository(Repository[Finding]):
    model = Finding

    async def for_campaign(self, campaign_id: uuid.UUID) -> Sequence[Finding]:
        stmt = self._base_query().where(Finding.campaign_id == campaign_id)
        return (await self.session.execute(stmt)).scalars().all()


class RecommendationRepository(Repository[Recommendation]):
    model = Recommendation

    async def for_finding(self, finding_id: uuid.UUID) -> Sequence[Recommendation]:
        stmt = select(Recommendation).where(Recommendation.finding_id == finding_id)
        return (await self.session.execute(stmt)).scalars().all()


class RemediationRunRepository(Repository[RemediationRun]):
    model = RemediationRun


class ReportRepository(Repository[Report]):
    model = Report

    async def for_subject(self, subject_type: str, subject_id: uuid.UUID) -> Report | None:
        """取某主体当前生效的报告；同主体历史重复行只认版本最高、最新创建的那份。

        早年两个生成端点直接 insert，库里留下了同主体多行。这里必须收敛成确定性的
        单行查询：否则 scalar_one_or_none 会抛 MultipleResultsFound，重新生成报告
        时直接 500。
        """
        stmt = (
            self._base_query()
            .where(Report.subject_type == subject_type, Report.subject_id == subject_id)
            .order_by(Report.version.desc(), Report.created_at.desc(), Report.id.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalars().first()


class ReportExportRepository(Repository[ReportExport]):
    model = ReportExport


class NotificationRepository(Repository[Notification]):
    model = Notification

    async def pending(self) -> Sequence[Notification]:
        stmt = select(Notification).where(Notification.status == "pending").limit(200)
        return (await self.session.execute(stmt)).scalars().all()


class SubscriptionRepository(Repository[Subscription]):
    model = Subscription


class GateRuleRepository(Repository[GateRule]):
    model = GateRule


class ScoreRepository(Repository[Score]):
    model = Score

    async def latest_for(self, subject_type: str, subject_id: uuid.UUID) -> Score | None:
        stmt = (
            select(Score)
            .where(Score.subject_type == subject_type, Score.subject_id == subject_id)
            .order_by(Score.computed_at.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def segment_scores(self, segment: str) -> Sequence[Score]:
        stmt = select(Score).where(Score.segment == segment).order_by(Score.computed_at.desc())
        return (await self.session.execute(stmt)).scalars().all()


class PresetRepository(Repository[Preset]):
    model = Preset

    async def by_code(self, code: str) -> Preset | None:
        stmt = select(Preset).where(Preset.code == code)
        return (await self.session.execute(stmt)).scalar_one_or_none()


class VerificationRecordRepository(Repository[VerificationRecord]):
    model = VerificationRecord


class HealthCheckRepository(Repository[HealthCheck]):
    model = HealthCheck


class AgentCredentialRepository(Repository[AgentCredential]):
    model = AgentCredential


class AuditLogRepository(Repository[AuditLog]):
    model = AuditLog

class ScanJobRepository(Repository[ScanJob]):
    model = ScanJob

    async def list_by_tenant(self, tenant_id: uuid.UUID, limit: int = 50) -> Sequence[ScanJob]:
        stmt = (
            select(ScanJob)
            .where(ScanJob.tenant_id == tenant_id)
            .order_by(ScanJob.created_at.desc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_running(self) -> Sequence[ScanJob]:
        stmt = select(ScanJob).where(ScanJob.status.in_(("pending", "running")))
        return (await self.session.execute(stmt)).scalars().all()


class ChangeSignalRepository(Repository[ChangeSignal]):
    model = ChangeSignal

    async def list_by_agent(self, agent_id: uuid.UUID, limit: int = 50) -> Sequence[ChangeSignal]:
        stmt = (
            select(ChangeSignal)
            .where(ChangeSignal.agent_id == agent_id)
            .order_by(ChangeSignal.detected_at.desc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()

    async def list_pending(self) -> Sequence[ChangeSignal]:
        stmt = select(ChangeSignal).where(ChangeSignal.verification_status == "pending")
        return (await self.session.execute(stmt)).scalars().all()


class AlertRepository(Repository[Alert]):
    model = Alert

    async def list_unacknowledged(self, tenant_id: uuid.UUID | None = None) -> Sequence[Alert]:
        stmt = select(Alert).where(Alert.acknowledged.is_(False))
        if tenant_id is not None:
            stmt = stmt.where(Alert.tenant_id == tenant_id)
        stmt = stmt.order_by(Alert.created_at.desc())
        return (await self.session.execute(stmt)).scalars().all()

class VerdictRepository(Repository[Verdict]):
    model = Verdict

    async def list_for_record(self, record_id: uuid.UUID) -> Sequence[Verdict]:
        return await self.list_by(record_id=record_id)


class TraceEventRepository(Repository[TraceEvent]):
    model = TraceEvent

    async def recent_for_tenant(self, tenant_id: uuid.UUID, limit: int = 100) -> Sequence[TraceEvent]:
        stmt = (
            select(TraceEvent)
            .where(TraceEvent.tenant_id == tenant_id)
            .order_by(TraceEvent.ts.desc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()


class JudgeCallRepository(Repository[JudgeCall]):
    model = JudgeCall


class EgressLogRepository(Repository[EgressLog]):
    model = EgressLog

    async def recent_for_tenant(self, tenant_id: uuid.UUID, limit: int = 100) -> Sequence[EgressLog]:
        stmt = (
            select(EgressLog)
            .where(EgressLog.tenant_id == tenant_id)
            .order_by(EgressLog.ts.desc())
            .limit(limit)
        )
        return (await self.session.execute(stmt)).scalars().all()
