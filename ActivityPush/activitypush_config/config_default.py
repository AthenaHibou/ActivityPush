"""ActivityPush 插件默认配置项定义"""
from typing import Dict

from gsuid_core.utils.plugins_config.models import (
    GSC,
    GsBoolConfig,
    GsIntConfig,
    GsListStrConfig,
    GsStrConfig,
)

CONFIG_DEFAULT: Dict[str, GSC] = {
    "command_keyword": GsStrConfig(
        title="指令关键字",
        desc="用户命令前缀，如 >活动查询。改后需重启 Core 生效",
        data=">",
    ),
    "api_base": GsStrConfig(
        title="API 地址",
        desc="StarRailAssistant 公开 API 基础地址",
        data="https://starrailassistant.top/api/v1",
    ),
    "fetch_interval": GsIntConfig(
        title="拉取间隔（分钟）",
        desc="定时拉取活动数据的间隔，默认 360 分钟（6 小时）",
        data=360,
        max_value=1440,
    ),
    "remind_days": GsListStrConfig(
        title="提醒天数",
        desc="活动剩余天数达到这些值时触发提醒（如 3,2,1）",
        data=["3", "2", "1"],
    ),
    "enable_group_push": GsBoolConfig(
        title="启用群级到期推送",
        desc="开启后，订阅了「>开启活动推送」的群会在活动临近结束时收到汇总推送",
        data=True,
    ),
    "enable_user_remind": GsBoolConfig(
        title="启用个人提醒",
        desc="开启后，AI/命令创建的个人活动提醒才会在到期时 @ 用户",
        data=True,
    ),
    "enable_game_sr": GsBoolConfig(
        title="崩坏：星穹铁道",
        desc="是否启用该游戏的活动数据",
        data=True,
    ),
    "enable_game_ys": GsBoolConfig(
        title="原神",
        desc="是否启用该游戏的活动数据",
        data=True,
    ),
    "enable_game_zzz": GsBoolConfig(
        title="绝区零",
        desc="是否启用该游戏的活动数据",
        data=True,
    ),
    "enable_game_ww": GsBoolConfig(
        title="鸣潮",
        desc="是否启用该游戏的活动数据",
        data=True,
    ),
    "enable_game_nte": GsBoolConfig(
        title="异环",
        desc="是否启用该游戏的活动数据",
        data=True,
    ),
    "enable_game_ef": GsBoolConfig(
        title="明日方舟：终末地",
        desc="是否启用该游戏的活动数据",
        data=True,
    ),
}
