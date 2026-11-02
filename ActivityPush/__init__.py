"""init"""
from gsuid_core.sv import Plugins

from .activitypush_config.activity_config import AP_CONFIG

# 指令关键字：默认 ">"，可在 web 控制台「插件配置」里修改，改后需重启 Core 生效
KEYWORD: str = AP_CONFIG.get_config("command_keyword").data or ">"

Plugins(
    name="ActivityPush",
    force_prefix=[KEYWORD],
    allow_empty_prefix=False,
    alias=["活动"],
)

# 业务子模块（显式 import 保证注册顺序确定；模块有缓存，重复导入无害）
from . import activitypush_main  # noqa: F401,E402
from . import activitypush_ai  # noqa: F401,E402
from . import activitypush_reminder  # noqa: F401,E402
from . import activitypush_help  # noqa: F401,E402
from .utils.database import models  # noqa: F401,E402
