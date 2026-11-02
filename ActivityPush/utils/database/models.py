"""ActivityPush 数据模型"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field

from gsuid_core.utils.database.base_models import BaseModel, with_session
from gsuid_core.webconsole.mount_app import GsAdminModel, PageSchema, site


class ActivityReminder(BaseModel, table=True):
    """活动个人提醒表（AI / 命令创建，到期 @ 用户）"""

    __table_args__ = {"extend_existing": True}

    game: str = Field(title="游戏标识", default="")
    activity_name: str = Field(title="活动名称", default="")
    activity_end_time: str = Field(title="活动结束时间", default="")
    group_id: str = Field(title="群号（空=私聊）", default="")
    user_type: str = Field(title="会话类型", default="group")
    notified_days: str = Field(title="已通知天数", default="")
    status: str = Field(title="状态", default="active")
    created_at: str = Field(title="创建时间", default="")

    @classmethod
    @with_session
    async def create_reminder(
        cls,
        session: AsyncSession,
        user_id: str,
        bot_id: str,
        game: str,
        activity_name: str,
        activity_end_time: str,
        group_id: str,
        user_type: str,
    ) -> "ActivityReminder":
        """创建一条个人活动提醒"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        obj = cls(
            user_id=user_id,
            bot_id=bot_id,
            game=game,
            activity_name=activity_name,
            activity_end_time=activity_end_time,
            group_id=group_id,
            user_type=user_type,
            notified_days="",
            status="active",
            created_at=now,
        )
        session.add(obj)
        return obj

    @classmethod
    @with_session
    async def get_user_reminders(
        cls, session: AsyncSession, user_id: str, bot_id: str
    ) -> List["ActivityReminder"]:
        """获取用户全部提醒（按创建时间倒序）"""
        stmt = (
            select(cls)
            .where(cls.user_id == user_id)
            .where(cls.bot_id == bot_id)
            .where(cls.status == "active")
            .order_by(cls.id.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    @with_session
    async def get_active_reminders(cls, session: AsyncSession) -> List["ActivityReminder"]:
        """获取所有未结束的提醒（定时任务用）"""
        stmt = select(cls).where(cls.status == "active")
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    @with_session
    async def get_by_id(cls, session: AsyncSession, rid: int) -> Optional["ActivityReminder"]:
        stmt = select(cls).where(cls.id == rid)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    @with_session
    async def find_by_keyword(
        cls, session: AsyncSession, user_id: str, bot_id: str, keyword: str
    ) -> Optional["ActivityReminder"]:
        """按活动名关键词模糊匹配用户最近的一条提醒"""
        reminders = await cls.get_user_reminders(user_id, bot_id)
        kw = keyword.strip()
        if not kw:
            return reminders[0] if reminders else None
        for r in reminders:
            if kw in r.activity_name or r.activity_name in kw:
                return r
        return None

    @classmethod
    @with_session
    async def close_reminder(cls, session: AsyncSession, rid: int) -> bool:
        """关闭提醒（标记 done）"""
        obj = await cls.get_by_id(rid)
        if obj is None:
            return False
        obj.status = "done"
        session.add(obj)
        return True

    @classmethod
    @with_session
    async def mark_notified(cls, session: AsyncSession, rid: int, day: int) -> None:
        """记录某天数已通知，避免重复推送"""
        obj = await cls.get_by_id(rid)
        if obj is None:
            return
        days = [d for d in obj.notified_days.split(",") if d]
        if str(day) not in days:
            days.append(str(day))
        obj.notified_days = ",".join(days)
        session.add(obj)

    @classmethod
    @with_session
    async def mark_done(cls, session: AsyncSession, rid: int) -> None:
        """标记提醒结束（活动已过期 / 取消）"""
        obj = await cls.get_by_id(rid)
        if obj is None:
            return
        obj.status = "done"
        session.add(obj)


@site.register_admin
class ActivityReminderAdmin(GsAdminModel):
    pk_name = "id"
    page_schema = PageSchema(
        label="ActivityPush 提醒管理",
        icon="fa fa-bell",
    )  # type: ignore
    model = ActivityReminder
