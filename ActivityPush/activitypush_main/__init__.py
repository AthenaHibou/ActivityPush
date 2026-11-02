"""ActivityPush 用户命令（纯用户触发；AI 调用走 activitypush_ai 的 @ai_tools 工具）"""
from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.sv import SV

from ..activitypush_api import get_activity_data
from ..activitypush_reminder import (
    close_personal_reminder,
    create_personal_reminder,
    get_remind_days,
    list_personal_reminders,
    subscribe_group_push,
    unsubscribe_group_push,
)
from ..activitypush_render import render_activity_card, render_version_card
from ..utils.game import GAME_MAP, parse_game

sv = SV("活动查询")

_GAME_HINT = "支持游戏：" + " / ".join(GAME_MAP.values())
_QUERY_HINT = (
    "用法：>活动查询 <游戏> [活动关键词]\n"
    "例如：>活动查询 原神\n"
    "      >活动查询 崩铁 反贪\n" + _GAME_HINT
)


@sv.on_command(("活动查询", "查询活动"))
async def activity_query(bot: Bot, ev: Event) -> None:
    text = ev.text.strip()
    parts = text.split(maxsplit=1)
    if not parts:
        return await bot.send(_QUERY_HINT)
    parsed = parse_game(parts[0])
    if parsed is None:
        return await bot.send(f"暂不支持的游戏：{parts[0]}\n{_GAME_HINT}")
    game, _ = parsed
    keyword = parts[1] if len(parts) > 1 else ""
    data = await get_activity_data(game)
    if isinstance(data, str):
        return await bot.send(data)
    im = await render_activity_card(game, data, keyword, get_remind_days())
    await bot.send(im)


@sv.on_command(("版本查询", "查版本"))
async def version_query(bot: Bot, ev: Event) -> None:
    text = ev.text.strip()
    if not text:
        return await bot.send(f"用法：>版本查询 <游戏>，例如：>版本查询 原神\n{_GAME_HINT}")
    parsed = parse_game(text)
    if parsed is None:
        return await bot.send(f"暂不支持的游戏：{text}\n{_GAME_HINT}")
    game, _ = parsed
    data = await get_activity_data(game)
    if isinstance(data, str):
        return await bot.send(data)
    im = await render_version_card(game, data)
    await bot.send(im)


@sv.on_command(("活动提醒", "开启活动提醒"))
async def activity_remind(bot: Bot, ev: Event) -> None:
    text = ev.text.strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return await bot.send("用法：>活动提醒 <游戏> <活动名>\n例如：>活动提醒 原神 新芽相助")
    parsed = parse_game(parts[0])
    if parsed is None:
        return await bot.send(f"暂不支持的游戏：{parts[0]}\n{_GAME_HINT}")
    game, _ = parsed
    _, msg = await create_personal_reminder(ev, game, parts[1])
    await bot.send(msg)


@sv.on_command(("关闭活动提醒", "取消活动提醒"))
async def activity_remind_close(bot: Bot, ev: Event) -> None:
    _, msg = await close_personal_reminder(ev, ev.text)
    await bot.send(msg)


@sv.on_fullmatch("我的提醒")
async def my_reminders(bot: Bot, ev: Event) -> None:
    await bot.send(await list_personal_reminders(ev))


@sv.on_fullmatch("开启活动推送")
async def open_group_push(bot: Bot, ev: Event) -> None:
    await bot.send(await subscribe_group_push(ev))


@sv.on_fullmatch("关闭活动推送")
async def close_group_push(bot: Bot, ev: Event) -> None:
    await bot.send(await unsubscribe_group_push(ev))
