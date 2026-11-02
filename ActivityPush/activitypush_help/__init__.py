"""init"""
from gsuid_core.bot import Bot
from gsuid_core.help.utils import register_help
from gsuid_core.models import Event
from gsuid_core.sv import SV, get_plugin_available_prefix

from .get_help import get_activity_help

sv = SV("活动帮助")


@sv.on_fullmatch("活动帮助")
async def activity_help(bot: Bot, ev: Event) -> None:
    await bot.send(await get_activity_help())


register_help(
    "ActivityPush",
    f"{get_plugin_available_prefix('ActivityPush')}活动帮助",
)
