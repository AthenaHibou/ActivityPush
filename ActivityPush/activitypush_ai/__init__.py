"""ActivityPush 纯 AI 工具（@ai_tools，纯文本返回，covers/aliases 强化召回）

to_ai 触发器不支持 covers/aliases，当对话里出现特定游戏名（如"异环/绝区零"）时，
容易被其它游戏专属插件的工具挤掉召回。这里改为独立的 @ai_tools，并显式声明
数据覆盖面（covers）与领域问法（aliases），确保"活动查询/版本/到期提醒"这类诉求
能稳定被 AI 主 Agent 召回，且只返回文本（不渲染图片，避免额外延迟）。
"""
from gsuid_core.ai_core.register import ai_tools
from gsuid_core.models import Event

from ..activitypush_api import (
    build_activity_text,
    build_version_text,
    get_activity_data,
)
from ..activitypush_reminder import (
    close_personal_reminder,
    create_personal_reminder,
    list_personal_reminders,
)
from ..utils.game import GAME_MAP, parse_game

_GAME_HINT = "支持游戏：" + " / ".join(GAME_MAP.values())


@ai_tools(
    category="common",
    capability_domain="游戏活动",
    covers=[
        "原神/星穹铁道(崩铁)/绝区零/鸣潮/异环/终末地（sr/ys/zzz/ww/nte/ef）的活动列表、活动名称、活动起止时间、剩余天数、即将结束的活动",
        "任意游戏的当前版本号、版本名称、版本起止时间",
        "这周/下周/最近要到期的活动",
    ],
    aliases=["游戏·活动查询", "游戏·活动列表", "游戏·活动结束时间", "游戏·活动到期", "游戏·活动快结束了"],
)
async def query_activities(game: str, keyword: str = "") -> str:
    """查询指定游戏的当前版本与活动。

    当用户询问"xx游戏有哪些活动"、"xx活动什么时候结束"、"这周哪些活动要到期"、"xx游戏活动快结束了"时调用。
    若要创建活动提醒，请先用本工具确认活动的准确名称与结束时间。
    回复务必用一两句口语，直接说最临近的活动的名字和"剩几天"；禁止用 Markdown 表格、加粗、编号列表，不要罗列大量日期数字。

    Args:
        game: 游戏名称或标识，如 "原神"、"崩铁"、"绝区零"、"鸣潮"、"异环"、"终末地"、"zzz"、"sr/ys/zzz/ww/nte/ef"
        keyword: 可选活动关键词（模糊匹配活动名），默认空
    """
    parsed = parse_game(game)
    if parsed is None:
        return f"暂不支持的游戏：{game}\n{_GAME_HINT}"
    gid, _ = parsed
    data = await get_activity_data(gid)
    if isinstance(data, str):
        return data
    return build_activity_text(gid, data, keyword)


@ai_tools(
    category="common",
    capability_domain="游戏活动",
    covers=["任意游戏的当前版本号、版本名称、版本起止时间"],
    aliases=["游戏·版本查询", "游戏·版本信息", "游戏·版本时间"],
)
async def query_version(game: str) -> str:
    """查询指定游戏的版本信息（纯文本）。

    当用户询问"xx游戏现在什么版本"、"xx游戏版本什么时候更新/结束"时调用。
    一行口语作答即可，禁止 Markdown 表格/加粗/编号列表。

    Args:
        game: 游戏名称，如 "原神"、"崩铁"、"zzz"、"鸣潮"、"异环"、"终末地"
    """
    parsed = parse_game(game)
    if parsed is None:
        return f"暂不支持的游戏：{game}\n{_GAME_HINT}"
    gid, _ = parsed
    data = await get_activity_data(gid)
    if isinstance(data, str):
        return data
    return build_version_text(gid, data)


@ai_tools(
    category="common",
    capability_domain="游戏活动",
    covers=[
        "为当前用户创建活动到期提醒：活动剩余 3/2/1 天时在群里 @ 该用户",
        "活动倒计时提醒、活动快结束提醒我",
    ],
    aliases=["游戏·活动提醒", "游戏·活动到期提醒", "游戏·提醒我做活动", "活动快结束提醒我"],
)
async def create_activity_reminder(ev: Event, game: str, activity_name: str) -> str:
    """为用户创建活动到期提醒（活动剩余 3/2/1 天时在群里 @ 该用户）。

    当用户说"xx活动快结束了提醒我"、"xx活动还有几天结束提醒我"、"记得提醒我做xx活动"时调用。
    建议先用 query_activities 确认活动准确名称。

    Args:
        game: 游戏名称，如 "原神"、"崩铁"、"绝区零"、"鸣潮"、"异环"、"终末地"
        activity_name: 活动名称（可模糊匹配）
    """
    parsed = parse_game(game)
    if parsed is None:
        return f"暂不支持的游戏：{game}\n{_GAME_HINT}"
    gid, _ = parsed
    _, msg = await create_personal_reminder(ev, gid, activity_name)
    return msg


@ai_tools(
    category="common",
    capability_domain="游戏活动",
    covers=["关闭/取消用户的活动到期提醒"],
    aliases=["游戏·关闭活动提醒", "游戏·取消活动提醒", "游戏·做完了", "游戏·已完成"],
)
async def close_activity_reminder(ev: Event, activity_name: str = "") -> str:
    """关闭用户的活动到期提醒。当用户回复"做完了"、"已完成"、"不用提醒了"、"取消xx活动提醒"时调用。

    Args:
        activity_name: 活动名称关键词（可留空，留空则关闭最近一条提醒）
    """
    _, msg = await close_personal_reminder(ev, activity_name)
    return msg


@ai_tools(
    category="common",
    capability_domain="游戏活动",
    covers=["列出当前用户的所有活动到期提醒"],
    aliases=["游戏·我的活动提醒", "游戏·我的提醒列表"],
)
async def list_my_reminders(ev: Event) -> str:
    """列出当前用户所有活动到期提醒。当用户询问"我的活动提醒"、"我有哪些提醒"时调用。"""
    return await list_personal_reminders(ev)
