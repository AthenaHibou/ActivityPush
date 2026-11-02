"""ActivityPush 帮助图渲染"""
import json
from pathlib import Path
from typing import Dict

import aiofiles
from PIL import Image

from gsuid_core.help.draw_new_plugin_help import get_new_help
from gsuid_core.help.model import PluginHelp
from gsuid_core.help.utils import ICON
from gsuid_core.sv import get_plugin_available_prefix

from ..version import ActivityPush_version

HELP_DATA = Path(__file__).parent / "help.json"


async def get_help_data() -> Dict[str, PluginHelp]:
    async with aiofiles.open(HELP_DATA, "rb") as file:
        return json.loads(await file.read())


async def get_activity_help() -> bytes:
    help_data = await get_help_data()
    prefix = get_plugin_available_prefix("ActivityPush")
    return await get_new_help(
        plugin_name="ActivityPush",
        plugin_info={f"v{ActivityPush_version}": ""},
        plugin_icon=Image.open(ICON),
        plugin_help=help_data,
        plugin_prefix=f"{prefix}活动帮助",
        help_mode="dark",
    )
