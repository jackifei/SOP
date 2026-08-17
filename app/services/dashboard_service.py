from __future__ import annotations

import random
from dataclasses import dataclass

from .production_stats_service import ProductionStatsService


@dataclass
class DashboardStep:
    name: str
    roi: str
    label: str
    status: str
    duration: str


@dataclass
class DashboardSnapshot:
    template_name: str
    ok: int
    ng: int
    today: int
    week: int
    month: int
    ok_rate: float
    steps: list[DashboardStep]
    rois: list[tuple[int, int, int, int]]
    runtime: str
    shift_output: int
    average_cycle: str
    device_state: str


class DashboardService:
    """运行看板模拟数据服务。

    后续可替换为数据库查询、Redis 缓存或 MES 实时统计接口。
    """

    TEMPLATES = {
        "默认产品A": {
            "ok": 1236,
            "ng": 42,
            "today": 87,
            "week": 512,
            "month": 2018,
            "ok_rate": 96.7,
            "runtime": "08:26:17",
            "shift_output": 342,
            "average_cycle": "2.38 s",
            "device_state": "运行中",
            "steps": [
                DashboardStep("第一次检测", "ROI-1：左上", "person", "已完成", "0.82 s"),
                DashboardStep("第二次检测", "ROI-3：中间", "defect", "执行中", "1.16 s"),
                DashboardStep("结果输出", "全图", "result", "待执行", "--"),
                DashboardStep("MES 上报", "全图", "mes", "待执行", "--"),
            ],
            "rois": [(80, 70, 240, 180), (350, 90, 220, 190)],
        },
        "产品B": {
            "ok": 888,
            "ng": 23,
            "today": 61,
            "week": 389,
            "month": 1543,
            "ok_rate": 97.4,
            "runtime": "05:42:08",
            "shift_output": 251,
            "average_cycle": "2.71 s",
            "device_state": "运行中",
            "steps": [
                DashboardStep("第一次检测", "ROI-2：右上", "glove", "已完成", "0.91 s"),
                DashboardStep("手势确认", "ROI-4：左下", "gesture", "执行中", "0.63 s"),
                DashboardStep("结果输出", "全图", "result", "待执行", "--"),
            ],
            "rois": [(120, 80, 260, 200), (390, 130, 210, 170)],
        },
    }

    def __init__(self) -> None:
        self.stats = ProductionStatsService()

    def set_count_mode(self, mode: str) -> None:
        self.stats.set_count_mode(mode)

    def add_ok_result(self) -> None:
        self.stats.add_ok()

    def add_ng_result(self) -> None:
        self.stats.add_ng()

    def snapshot(self, template_name: str) -> DashboardSnapshot:
        data = self.TEMPLATES.get(template_name, self.TEMPLATES["默认产品A"])
        stats = self.stats.snapshot()
        return DashboardSnapshot(
            template_name=template_name,
            ok=stats["ok"],
            ng=stats["ng"],
            today=stats["today"],
            week=stats["week"],
            month=stats["month"],
            ok_rate=stats["ok_rate"],
            steps=data["steps"],
            rois=data["rois"],
            runtime=data["runtime"],
            shift_output=data["shift_output"],
            average_cycle=data["average_cycle"],
            device_state=data["device_state"],
        )

    def refresh(self, template_name: str) -> DashboardSnapshot:
        """模拟一次实时刷新。

        插入点：替换为真实统计接口或数据库查询后，保留 snapshot 数据结构即可。
        """
        self.stats.simulate_refresh()
        return self.snapshot(template_name)
