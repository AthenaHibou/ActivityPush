"""ActivityPush 图片渲染（PIL）"""
from typing import List

from PIL import Image, ImageDraw

from gsuid_core.utils.fonts.fonts import core_font
from gsuid_core.utils.image.convert import convert_img
from gsuid_core.utils.image.image_tools import get_color_bg

from ..activitypush_api import days_left, find_activities, format_time
from ..utils.game import GAME_MAP

_W = 950
_M = 46
_HEADER_H = 170
_ROW_H = 92


def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _truncate(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> str:
    if _text_width(draw, text, font) <= max_w:
        return text
    ellipsis = "…"
    while text and _text_width(draw, text + ellipsis, font) > max_w:
        text = text[:-1]
    return text + ellipsis


def _draw_days_badge(
    draw: ImageDraw.ImageDraw,
    days_left_val: int,
    remind_days: List[int],
    x: int,
    y: int,
) -> None:
    if days_left_val < 0:
        text = "已结束"
        color = (120, 120, 120)
    elif days_left_val == 0:
        text = "今天结束"
        color = (220, 60, 60)
    elif days_left_val in remind_days:
        text = f"剩 {days_left_val} 天"
        color = (235, 150, 40) if days_left_val > 1 else (220, 60, 60)
    else:
        text = f"剩 {days_left_val} 天"
        color = (90, 160, 90)
    font = core_font(24, weight=700)
    tw = _text_width(draw, text, font)
    w = tw + 28
    h = 40
    draw.rounded_rectangle((x, y, x + w, y + h), radius=20, fill=color)
    draw.text((x + 14, y + 7), text, font=font, fill="white")


async def render_activity_card(
    game: str, data: dict, keyword: str, remind_days: List[int]
) -> bytes:
    """渲染活动列表卡片"""
    game_name = GAME_MAP[game]
    version = data["version"]
    version_name = data["versionName"]
    ver_start = format_time(data["startTime"])
    ver_end = format_time(data["endTime"])
    activities = find_activities(data["activities"], keyword)

    height = _HEADER_H + len(activities) * _ROW_H + 60
    img = await get_color_bg(based_w=_W, based_h=height, is_full=True)
    draw = ImageDraw.Draw(img)

    title_font = core_font(46, weight=700)
    sub_font = core_font(28)
    time_font = core_font(22, weight=500)
    name_font = core_font(30, weight=600)

    title = f"{game_name} · 当前活动"
    if keyword:
        title += f"（筛选：{keyword}）"
    draw.text((_M, 40), title, font=title_font, fill="white")
    draw.text((_M, 104), f"版本 {version} · {version_name}", font=sub_font, fill=(235, 235, 235))
    draw.text((_M, 140), f"版本时间：{ver_start} ~ {ver_end}", font=time_font, fill=(180, 180, 180))
    draw.line((_M, _HEADER_H - 18, _W - _M, _HEADER_H - 18), fill=(255, 255, 255, 70), width=2)

    if not activities:
        draw.text((_M, _HEADER_H + 30), "未找到匹配的活动", font=sub_font, fill=(200, 200, 200))
    else:
        time_small_font = core_font(22, weight=400)
        for i, act in enumerate(activities):
            y = _HEADER_H + i * _ROW_H
            name = act["name"]
            start = format_time(act["startTime"])
            end = format_time(act["endTime"])
            dl = days_left(act["endTime"])

            draw.text(
                (_M, y + 16),
                _truncate(draw, name, name_font, _W - 2 * _M - 140),
                font=name_font,
                fill="white",
            )
            draw.text((_M, y + 56), f"{start} ~ {end}", font=time_small_font, fill=(190, 190, 190))
            _draw_days_badge(draw, dl, remind_days, _W - _M - 130, y + 24)

    return await convert_img(img)


async def render_version_card(game: str, data: dict) -> bytes:
    """渲染版本信息卡片"""
    game_name = GAME_MAP[game]
    width = 750
    height = 320

    img = await get_color_bg(based_w=width, based_h=height, is_full=True)
    draw = ImageDraw.Draw(img)

    title_font = core_font(44, weight=700)
    big_font = core_font(40, weight=700)
    sub_font = core_font(28)
    time_font = core_font(24, weight=500)

    draw.text((_M, 48), f"{game_name} · 版本信息", font=title_font, fill="white")
    draw.text((_M, 130), f"版本号：{data['version']}", font=big_font, fill=(255, 220, 120))
    draw.text((_M, 190), f"版本名：{data['versionName']}", font=sub_font, fill=(235, 235, 235))
    draw.text(
        (_M, 245),
        f"版本时间：{format_time(data['startTime'])} ~ {format_time(data['endTime'])}",
        font=time_font,
        fill=(180, 180, 180),
    )

    return await convert_img(img)
