"""活动提醒 / 群级推送：gs_subscribe 订阅管理 + 定时任务"""
import json
from pathlib import Path
from typing import Dict, List, Tuple

from gsuid_core.aps import scheduler
from gsuid_core.logger import logger
from gsuid_core.pool import to_thread
from gsuid_core.segment import MessageSegment
from gsuid_core.subscribe import gs_subscribe
from gsuid_core.utils.database.models import Subscribe

from ..activitypush_config.activity_config import AP_CONFIG
from ..activitypush_api import days_left, find_activities, format_time, get_activity_data, get_enabled_games
from ..utils.database.models import ActivityReminder
from ..utils.game import GAME_MAP
from ..utils.resource.RESOURCE_PATH import DATA_PATH

PERSONAL_TASK = "[ActivityPush] 个人提醒"
GROUP_TASK = "[ActivityPush] 群到期推送"


def get_remind_days() -> List[int]:
    """解析提醒天数配置，返回降序 int 列表（如 [3, 2, 1]）"""
    cfg = AP_CONFIG.get_config("remind_days").data
    days: List[int] = []
    for d in cfg:
        try:
            days.append(int(d))
        except (TypeError, ValueError):
            continue
    return sorted(set(days), reverse=True)


# ---------- 个人提醒：创建 / 关闭 / 列表（命令与 AI 共用） ----------

async def create_personal_reminder(ev, game: str, activity_name: str) -> Tuple[bool, str]:
    """创建一条个人活动到期提醒"""
    if not AP_CONFIG.get_config("enable_user_remind").data:
        return False, "个人提醒功能未开启，可在 web 控制台「插件配置」中打开"
    data = await get_activity_data(game)
    if isinstance(data, str):
        return False, data
    acts = find_activities(data["activities"], activity_name)
    if not acts:
        return False, f"在{GAME_MAP[game]}中未找到活动「{activity_name}」"
    act = acts[0]
    name = act["name"]
    end = act["endTime"]
    dl = days_left(end)
    if dl < 0:
        return False, f"活动「{name}」已结束"
    existing = await ActivityReminder.get_user_reminders(ev.user_id, ev.bot_id)
    for r in existing:
        if r.game == game and r.activity_name == name:
            return False, f"已存在活动「{name}」的提醒"
    reminder = await ActivityReminder.create_reminder(
        user_id=ev.user_id,
        bot_id=ev.bot_id,
        game=game,
        activity_name=name,
        activity_end_time=end,
        group_id=ev.group_id or "",
        user_type=ev.user_type,
    )
    await gs_subscribe.add_subscribe(
        subscribe_type="single",
        task_name=PERSONAL_TASK,
        event=ev,
        extra_message=name,
    )
    return True, (
        f"✅ 已创建提醒：{GAME_MAP[game]}「{name}」\n"
        f"活动将于 {format_time(end)} 结束（剩 {dl} 天），到期前会提醒你。"
    )


async def close_personal_reminder(ev, keyword: str) -> Tuple[bool, str]:
    """关闭用户的一条活动提醒（按活动名模糊匹配）"""
    r = await ActivityReminder.find_by_keyword(ev.user_id, ev.bot_id, keyword)
    if r is None:
        return False, "未找到你的活动提醒"
    await ActivityReminder.close_reminder(r.id)
    await _cleanup_user_subscription(ev.user_id, ev.bot_id)
    return True, f"✅ 已关闭提醒：{GAME_MAP.get(r.game, r.game)}「{r.activity_name}」"


async def list_personal_reminders(ev) -> str:
    """列出用户全部活动提醒（文本）"""
    rs = await ActivityReminder.get_user_reminders(ev.user_id, ev.bot_id)
    if not rs:
        return "你还没有活动提醒，可以对 AI 说「原神的活动快结束了提醒我」来创建"
    lines = ["📋 你的活动提醒："]
    for r in rs:
        dl = days_left(r.activity_end_time)
        dl_text = "已结束" if dl < 0 else f"剩 {dl} 天"
        lines.append(
            f"{GAME_MAP.get(r.game, r.game)}｜{r.activity_name}"
            f"（{dl_text}，{format_time(r.activity_end_time)} 结束）"
        )
    lines.append("回复「做完了 活动名」可关闭对应提醒")
    return "\n".join(lines)


async def _cleanup_user_subscription(user_id: str, bot_id: str) -> None:
    """用户没有更多提醒时，删除其个人提醒订阅"""
    remaining = await ActivityReminder.get_user_reminders(user_id, bot_id)
    if remaining:
        return
    await Subscribe.delete_row(bot_id=bot_id, user_id=user_id, task_name=PERSONAL_TASK)


# ---------- 群级推送：订阅 / 退订 ----------

async def subscribe_group_push(ev) -> str:
    """开启当前群的活动到期推送"""
    if not AP_CONFIG.get_config("enable_group_push").data:
        return "群级推送功能未开启，可在 web 控制台「插件配置」中打开"
    if ev.user_type != "group" or not ev.group_id:
        return "该功能需在群聊中使用"
    await gs_subscribe.add_subscribe(
        subscribe_type="session",
        task_name=GROUP_TASK,
        event=ev,
    )
    return "✅ 本群已开启活动到期推送，活动临近结束时我会发汇总提醒"


async def unsubscribe_group_push(ev) -> str:
    """关闭当前群的活动到期推送"""
    await gs_subscribe.delete_subscribe("session", GROUP_TASK, ev)
    return "✅ 已关闭本群的活动到期推送"


# ---------- 群推送去重状态（持久化到磁盘，避免重启丢失） ----------

def _push_state_path() -> Path:
    return DATA_PATH / "group_push_state.json"


@to_thread
def _load_push_state() -> Dict[str, List[str]]:
    path = _push_state_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


@to_thread
def _save_push_state(state: Dict[str, List[str]]) -> None:
    _push_state_path().write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")


# ---------- 定时任务 ----------

async def _send_reminder(sub, r: ActivityReminder, dl: int) -> None:
    """向订阅会话推送个人提醒（群内 @ 用户 / 私聊纯文本）"""
    game_name = GAME_MAP.get(r.game, r.game)
    text = (
        f"⏰ 活动提醒：{game_name}「{r.activity_name}」\n"
        f"还剩 {dl} 天，将于 {format_time(r.activity_end_time)} 结束，记得去完成哦！\n"
        f"完成后来回复我：做完了 {r.activity_name}"
    )
    if sub.user_type == "group" and sub.user_id:
        await sub.send(reply=[MessageSegment.text(text), MessageSegment.at(sub.user_id)])
    else:
        await sub.send(reply=text)


@scheduler.scheduled_job("interval", minutes=30)
async def _check_user_reminders() -> None:
    """扫描个人提醒：命中 3/2/1 天阈值时 @ 用户；活动已结束则自动关闭"""
    if not AP_CONFIG.get_config("enable_user_remind").data:
        return
    remind_days = get_remind_days()
    if not remind_days:
        return
    try:
        reminders = await ActivityReminder.get_active_reminders()
        if not reminders:
            return
        subs = await gs_subscribe.get_subscribe(PERSONAL_TASK) or []
        sub_by_user: Dict[Tuple[str, str], object] = {}
        for s in subs:
            sub_by_user[(s.bot_id, s.user_id)] = s
        for r in reminders:
            dl = days_left(r.activity_end_time)
            if dl < 0:
                await ActivityReminder.mark_done(r.id)
                await _cleanup_user_subscription(r.user_id, r.bot_id)
                continue
            if dl not in remind_days:
                continue
            notified = [int(d) for d in r.notified_days.split(",") if d]
            if dl in notified:
                continue
            sub = sub_by_user.get((r.bot_id, r.user_id))
            if sub is None:
                continue
            await _send_reminder(sub, r, dl)
            await ActivityReminder.mark_notified(r.id, dl)
    except Exception as e:
        logger.exception(f"[ActivityPush] 个人提醒检查异常: {e}")


@scheduler.scheduled_job("interval", minutes=60)
async def _check_group_push() -> None:
    """向已订阅群推送即将结束的活动汇总（按 3/2/1 天阈值，已推送的跳过）"""
    if not AP_CONFIG.get_config("enable_group_push").data:
        return
    remind_days = get_remind_days()
    if not remind_days:
        return
    max_day = max(remind_days)
    try:
        subs = await gs_subscribe.get_subscribe(GROUP_TASK)
        if not subs:
            return
        upcoming: List[Tuple[str, str, int, str]] = []
        for game in get_enabled_games():
            data = await get_activity_data(game)
            if isinstance(data, str):
                continue
            for act in data["activities"]:
                dl = days_left(act["endTime"])
                if 0 <= dl <= max_day:
                    upcoming.append((GAME_MAP[game], act["name"], dl, act["endTime"]))
        if not upcoming:
            return
        upcoming.sort(key=lambda x: x[2])
        state = await _load_push_state()
        for sub in subs:
            key = sub.group_id or sub.user_id or "default"
            pushed = state.get(key, [])
            to_push = []
            for game_name, name, dl, end in upcoming:
                uid_key = f"{game_name}|{name}|{dl}"
                if uid_key not in pushed:
                    to_push.append((game_name, name, dl, end))
                    pushed.append(uid_key)
            if not to_push:
                continue
            lines = ["📢 活动到期提醒"]
            for game_name, name, dl, end in to_push:
                lines.append(f"{game_name}｜{name}（剩 {dl} 天，{format_time(end)} 结束）")
            keyword = AP_CONFIG.get_config("command_keyword").data or ">"
            lines.append(f"可在群里发送「{keyword}关闭活动推送」取消本群推送")
            await sub.send(reply="\n".join(lines))
            state[key] = pushed[-50:]
        await _save_push_state(state)
    except Exception as e:
        logger.exception(f"[ActivityPush] 群推送检查异常: {e}")
