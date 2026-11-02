"""游戏标识与中文名映射（数据源：StarRailAssistant 公开 API）"""
from typing import Dict, Tuple

# 游戏标识 -> 中文名
GAME_MAP: Dict[str, str] = {
    "sr": "崩坏：星穹铁道",
    "ys": "原神",
    "zzz": "绝区零",
    "ww": "鸣潮",
    "nte": "异环",
    "ef": "明日方舟：终末地",
}

# 用户输入别名 -> 游戏标识（尽量全量收录常见说法）
GAME_ALIAS: Dict[str, str] = {
    # 崩坏：星穹铁道
    "崩坏：星穹铁道": "sr",
    "崩坏星穹铁道": "sr",
    "星穹铁道": "sr",
    "星铁": "sr",
    "崩铁": "sr",
    "铁道": "sr",
    "sr": "sr",
    # 原神
    "原神": "ys",
    "原": "ys",
    "ys": "ys",
    "genshin": "ys",
    # 绝区零
    "绝区零": "zzz",
    "绝区": "zzz",
    "zzz": "zzz",
    # 鸣潮
    "鸣潮": "ww",
    "鸣": "ww",
    "ww": "ww",
    "wuthering": "ww",
    # 异环
    "异环": "nte",
    "环": "nte",
    "nte": "nte",
    # 明日方舟：终末地
    "终末地": "ef",
    "明日方舟：终末地": "ef",
    "明日方舟终末地": "ef",
    "方舟终末地": "ef",
    "ef": "ef",
    "endfield": "ef",
}


def parse_game(text: str) -> Tuple[str, str] | None:
    """把用户输入解析为 (game_id, 中文名)；解析失败返回 None。"""
    raw = text.strip().lower()
    if not raw:
        return None
    if raw in GAME_MAP:
        return raw, GAME_MAP[raw]
    gid = GAME_ALIAS.get(raw)
    if gid is not None:
        return gid, GAME_MAP[gid]
    return None
