"""StarRailAssistant 公开 API 客户端 + 缓存 + 定时拉取"""
import asyncio
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import httpx

from gsuid_core.aps import scheduler
from gsuid_core.logger import logger
from gsuid_core.pool import to_thread

from ..activitypush_config.activity_config import AP_CONFIG
from ..utils.game import GAME_MAP
from ..utils.resource.RESOURCE_PATH import DATA_PATH

# 内存缓存：{game: (拉取时间戳, 数据)}
_MEMORY_CACHE: Dict[str, Tuple[float, dict]] = {}
_REFRESH_LOCK = asyncio.Lock()

_TIMEOUT = httpx.Timeout(15.0, connect=8.0)

# 终末地版本活动日历（Endfield Version Calendar）API 基地址
_ENDFIELD_API = "https://ef-cal.mogujun.icu/api/v1/events"


def get_api_base() -> str:
    """API 基础地址（可配置）"""
    return AP_CONFIG.get_config("api_base").data or "https://starrailassistant.top/api/v1"


def get_fetch_interval_minutes() -> int:
    """拉取间隔（分钟）"""
    interval = AP_CONFIG.get_config("fetch_interval").data
    if isinstance(interval, int) and interval > 0:
        return interval
    return 360


def get_enabled_games() -> List[str]:
    """返回已启用的游戏标识列表（按配置开关）"""
    enabled = []
    for gid in GAME_MAP:
        cfg = AP_CONFIG.get_config(f"enable_game_{gid}")
        if cfg is not None and cfg.data:
            enabled.append(gid)
    return enabled


def _cache_path(game: str) -> Path:
    return DATA_PATH / f"{game}.json"


@to_thread
def _save_disk_cache(game: str, data: dict) -> None:
    _cache_path(game).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@to_thread
def _load_disk_cache(game: str) -> Tuple[dict, float] | None:
    """返回 (数据, 文件修改时间)；无缓存或解析失败返回 None"""
    path = _cache_path(game)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data, path.stat().st_mtime
    except (json.JSONDecodeError, OSError):
        logger.warning(f"[ActivityPush] 磁盘缓存读取失败: {path}")
        return None


def parse_iso_time(iso: str) -> datetime:
    """解析 ISO 8601 时间字符串"""
    return datetime.fromisoformat(iso)


def format_time(iso: str) -> str:
    """显示用时间：MM-DD HH:MM；空串（常驻无结束）返回空"""
    if not iso:
        return ""
    return parse_iso_time(iso).strftime("%m-%d %H:%M")


def days_left(end_iso: str) -> int:
    """剩余天数；无结束时间或已结束返回 -1"""
    if not end_iso:
        return -1
    end = parse_iso_time(end_iso)
    # 带时区偏移的 ISO（如终末地）与 naive 的 now 不能直接相减，需同侧对齐
    now = datetime.now(end.tzinfo) if end.tzinfo is not None else datetime.now()
    delta = end - now
    if delta.total_seconds() <= 0:
        return -1
    return math.ceil(delta.total_seconds() / 86400)


def find_activities(activities: List[dict], keyword: str) -> List[dict]:
    """按名称关键词过滤活动（空关键词返回全部）"""
    kw = keyword.strip()
    if not kw:
        return activities
    return [a for a in activities if kw in a["name"]]


def _sort_activities(acts: List[dict]) -> List[dict]:
    """按接近结束优先排序；已结束的排最后，避免[:8]把近期活动截掉"""
    def _key(a: dict) -> Tuple[int, int]:
        dl = days_left(a.get("endTime") or "")
        return (1 if dl < 0 else 0, dl if dl >= 0 else 0)

    return sorted(acts, key=_key)


def build_activity_text(game: str, data: dict, keyword: str) -> str:
    """活动数据 -> 平铺短行（无表格/无加粗，框架念数闸门已按需放行）"""
    game_name = GAME_MAP[game]
    acts = _sort_activities(find_activities(data["activities"], keyword))
    if not acts:
        return f"暂无{game_name}的活动"
    # 只留未结束的近期活动，按临近结束排前；无未结束时兜底用全部
    live = [a for a in acts if days_left(a.get("endTime") or "") >= 0]
    if not live:
        return f"{game_name}当前没有进行中或未开始的活动"
    top = live[:5]
    lines = [f"{game_name}近期活动（按结束临近）："]
    for a in top:
        dl = days_left(a.get("endTime") or "")
        end_txt = format_time(a.get("endTime") or "")
        lines.append(f"{a.get('name', '未知活动')}：{end_txt}结束，剩{dl}天")
    if len(live) > len(top):
        lines.append(f"还有{len(live) - len(top)}个近期活动")
    return "\n".join(lines)


def build_version_text(game: str, data: dict) -> str:
    """版本数据 -> 纯文本摘要（供 AI 工具直接返回）"""
    game_name = GAME_MAP[game]
    return (
        f"【{game_name} 版本信息】\n"
        f"版本号: {data['version']}\n"
        f"版本名: {data['versionName']}\n"
        f"版本时间: {format_time(data['startTime'])} ~ {format_time(data['endTime'])}"
    )


def _endfield_version_end(ver: dict, events: List[dict]) -> str:
    """当前版本常无 endsAt，取本版本有结束时间的活动里最晚的兜底；无则空串"""
    if ver.get("endsAt"):
        return ver["endsAt"]
    ver_key = ver.get("versionKey")
    ends = [
        e.get("end")
        for e in events
        if e.get("versionKey") == ver_key and e.get("end")
    ]
    return max(ends) if ends else ""


async def _fetch_endfield() -> dict | str:
    """拉取终末地版本活动并归一化为统一数据形状；失败返回错误信息字符串"""
    _UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_UA) as client:
                resp = await client.get(_ENDFIELD_API, params={"status": "all"})
                if resp.status_code != 200:
                    return f"API 返回状态码 {resp.status_code}"
                payload = resp.json()
                break
        except Exception as e:  # 外部网络边界：TLS/代理/超时异常，重试一次再兜底
            logger.warning(f"[ActivityPush] 拉取 ef 活动失败(第{attempt + 1}次): {type(e).__name__}: {e!r}")
            payload = None
    if payload is None:
        return "网络请求失败"

    if not isinstance(payload, dict) or payload.get("success") is not True:
        return "终末地 API 返回数据格式异常"
    data = payload.get("data")
    if not isinstance(data, dict):
        return "终末地 API 返回数据格式异常"
    versions = data.get("versions", []) if isinstance(data.get("versions"), list) else []
    events = data.get("events", []) if isinstance(data.get("events"), list) else []
    active = data.get("activeVersionKey", "")

    ver = next((v for v in versions if v.get("versionKey") == active), None)
    if ver is None and versions:
        ver = versions[0]

    # 仅保留有时限的活动（常驻活动无结束时间，不属于"到期"范畴）
    activities = [
        {"name": e.get("title", "未知活动"), "startTime": e.get("start", ""), "endTime": e.get("end", "")}
        for e in events
        if e.get("end")
    ]

    return {
        "version": ver.get("versionNumber", "?") if ver else "?",
        "versionName": ver.get("title", "未知") if ver else "未知",
        "startTime": ver.get("startsAt", "") if ver else "",
        "endTime": _endfield_version_end(ver, events) if ver else "",
        "activities": activities,
    }


async def fetch_activity_from_api(game: str) -> dict | str:
    """从 API 拉取某游戏活动数据；失败返回错误信息字符串"""
    if game == "ef":
        return await _fetch_endfield()
    url = f"{get_api_base()}/activity/{game}.json"
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return f"API 返回状态码 {resp.status_code}"
            data = resp.json()
            if not isinstance(data, dict) or "activities" not in data:
                return "API 返回数据格式异常"
            return data
    except httpx.HTTPError as e:
        logger.warning(f"[ActivityPush] 拉取 {game} 活动失败: {e}")
        return f"网络请求失败：{type(e).__name__}"


async def get_activity_data(game: str, force: bool = False) -> dict | str:
    """获取活动数据：内存缓存 -> 磁盘缓存 -> 远程 API"""
    now = datetime.now().timestamp()
    interval = get_fetch_interval_minutes() * 60

    cached = _MEMORY_CACHE.get(game)
    if cached is not None and not force and (now - cached[0]) < interval:
        return cached[1]

    disk = await _load_disk_cache(game)
    if disk is not None and not force and (now - disk[1]) < interval:
        _MEMORY_CACHE[game] = (now, disk[0])
        return disk[0]

    data = await fetch_activity_from_api(game)
    if isinstance(data, str):
        # 远程失败：回退到磁盘缓存（若有）
        if disk is not None:
            _MEMORY_CACHE[game] = (now, disk[0])
            return disk[0]
        return data

    _MEMORY_CACHE[game] = (now, data)
    await _save_disk_cache(game, data)
    return data


async def refresh_all() -> None:
    """拉取所有已启用游戏的活动数据（定时任务）"""
    if _REFRESH_LOCK.locked():
        return
    async with _REFRESH_LOCK:
        games = get_enabled_games()
        ok = 0
        for game in games:
            data = await get_activity_data(game, force=True)
            if isinstance(data, dict):
                ok += 1
        logger.info(f"[ActivityPush] 定时拉取完成: {ok}/{len(games)} 个游戏成功")


@scheduler.scheduled_job("interval", minutes=get_fetch_interval_minutes())
async def _periodic_fetch() -> None:
    await refresh_all()
