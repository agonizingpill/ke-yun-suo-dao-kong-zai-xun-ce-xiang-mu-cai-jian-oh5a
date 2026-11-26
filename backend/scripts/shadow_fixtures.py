from datetime import date, timedelta
from random import Random

from lab.constants import Shift

CREW = (("duan", "段舟 · 空载记录", "technician"),
        ("ning", "宁芩 · 复核班长", "supervisor"),
        ("qin", "秦山 · 台账查阅", "viewer"))

# The locked set is a synthetic corpus fixture, not a checklist for actual equipment.
MEASURES = (
    ("K-11", "演示巡检凭证确认", "回执码", "训练目录 · K-11", True),
    ("K-12", "演示作业边界见证", "回执码", "训练目录 · K-12", True),
    ("K-13", "演示值守到位确认", "回执码", "训练目录 · K-13", True),
    ("O-21", "回看区间亮暗差", "相对值", "媒体工作站 · 灰度", False),
    ("O-22", "镜头门框偏心", "px", "媒体工作站 · 框差", False),
    ("O-23", "梭形标记点抖动", "px", "媒体工作站 · 跟踪", False),
    ("O-24", "记录板画面裁边", "px", "媒体工作站 · 裁边", False),
    ("O-25", "镜头片段反光段数", "段", "媒体工作站 · 对照", False),
    ("O-26", "时间牌偏移量", "帧", "媒体工作站 · 时间牌", False),
)

CUTOFF = date(2026, 11, 18)


def marks(label, rng):
    return [1, 1, 1, 15 + 40 * label + rng.uniform(-5, 5),
            24 + 28 * label + rng.uniform(-4, 4), rng.uniform(12, 21),
            rng.uniform(6, 18), rng.randint(0, 7), rng.randint(0, 34)]


def historical_runs():
    rng = Random(1080)
    for day in range(1, 19):
        for shift_index, shift in enumerate(Shift):
            label = (day + shift_index) % 2
            yield {"day": date(2026, 11, day), "ref": f"Y7-{day:02d}-{'A' if shift_index == 0 else 'P'}",
                   "shift": shift, "camera_review": bool(label)}, marks(label, rng)
    for offset, shift in enumerate(Shift, 1):
        yield {"day": CUTOFF + timedelta(days=offset), "ref": f"Y7-TRIAL-{offset}",
               "shift": shift, "camera_review": False}, marks(0, rng)
