from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import yaml


class ProductionStatsService:
    """生产统计服务。

    负责 OK/NG、日/周/月统计的持久化、周期清零、班次清零和 checknum 记录。
    """

    def __init__(self) -> None:
        self.root_dir = self._root_dir()
        self.stats_path = self.root_dir / "config" / "production_stats.yaml"
        self.checknum_dir = self.root_dir / "checknum"
        self.checknum_dir.mkdir(parents=True, exist_ok=True)
        self.stats_path.parent.mkdir(parents=True, exist_ok=True)
        self.data = self._load_stats()
        self.shifts = self._load_shifts()
        self.count_mode = self.data.get("count_mode", "日计数")
        self.check_period_reset()

    @staticmethod
    def _root_dir() -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parents[2]

    def _load_stats(self) -> dict:
        if not self.stats_path.exists():
            return self._default_stats()
        try:
            data = yaml.safe_load(self.stats_path.read_text(encoding="utf-8")) or {}
            default = self._default_stats()
            default.update(data)
            return default
        except (OSError, yaml.YAMLError):
            return self._default_stats()

    @staticmethod
    def _default_stats() -> dict:
        return {
            "count_mode": "日计数",
            "ok_total": 0,
            "ng_total": 0,
            "day_ok": 0,
            "day_ng": 0,
            "shift_ok": 0,
            "shift_ng": 0,
            "today": 0,
            "week": 0,
            "month": 0,
            "last_date": "",
            "last_week": "",
            "last_month": "",
            "last_shift": "",
        }

    def _load_shifts(self) -> list[dict]:
        path = self.root_dir / "config" / "shifts.yaml"
        if not path.exists():
            return [{"name": "默认班", "start": "00:00", "end": "23:59"}]
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
            return data if isinstance(data, list) else []
        except (OSError, yaml.YAMLError):
            return [{"name": "默认班", "start": "00:00", "end": "23:59"}]

    def save(self) -> None:
        self.data["count_mode"] = self.count_mode
        self.stats_path.write_text(
            yaml.safe_dump(self.data, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def set_count_mode(self, mode: str) -> None:
        self.count_mode = mode
        self.save()

    def current_ok(self) -> int:
        return self.data["shift_ok"] if self.count_mode == "班计数" else self.data["day_ok"]

    def current_ng(self) -> int:
        return self.data["shift_ng"] if self.count_mode == "班计数" else self.data["day_ng"]

    def snapshot(self) -> dict:
        self.check_period_reset()
        ok = self.current_ok()
        ng = self.current_ng()
        total = ok + ng
        ok_rate = round(ok / total * 100, 1) if total else 100.0
        return {
            "ok": ok,
            "ng": ng,
            "today": self.data["today"],
            "week": self.data["week"],
            "month": self.data["month"],
            "ok_rate": ok_rate,
        }

    def simulate_refresh(self) -> None:
        import random

        self.data["ok_total"] += random.randint(0, 2)
        self.data["ng_total"] += random.choice([0, 0, 1])
        self.data["day_ok"] += 1
        self.data["shift_ok"] += 1
        self.data["today"] += 1
        self.data["week"] += 1
        self.data["month"] += 1
        self.save()

    def add_ok(self) -> None:
        self.check_period_reset()
        self.data["ok_total"] += 1
        self.data["day_ok"] += 1
        self.data["shift_ok"] += 1
        self.data["today"] += 1
        self.data["week"] += 1
        self.data["month"] += 1
        self.save()

    def add_ng(self) -> None:
        self.check_period_reset()
        self.data["ng_total"] += 1
        self.data["day_ng"] += 1
        self.data["shift_ng"] += 1
        self.data["today"] += 1
        self.data["week"] += 1
        self.data["month"] += 1
        self.save()

    def check_period_reset(self) -> None:
        today = date.today()
        today_str = today.isoformat()
        week_key = f"{today.isocalendar()[0]}-{today.isocalendar()[1]}"
        month_key = today.strftime("%Y-%m")

        if self.data.get("last_date") != today_str:
            self._record_reset("day", self.data.get("today", 0))
            self.data["today"] = 0
            self.data["day_ok"] = 0
            self.data["day_ng"] = 0
            self.data["last_date"] = today_str

        if self.data.get("last_week") != week_key:
            self._record_reset("week", self.data.get("week", 0))
            self.data["week"] = 0
            self.data["last_week"] = week_key

        if self.data.get("last_month") != month_key:
            self._record_reset("month", self.data.get("month", 0))
            self.data["month"] = 0
            self.data["last_month"] = month_key

        shift_key = self._current_shift_key()
        if self.data.get("last_shift") != shift_key:
            self.data["shift_ok"] = 0
            self.data["shift_ng"] = 0
            self.data["last_shift"] = shift_key

        self.save()

    def _current_shift_key(self) -> str:
        now = datetime.now().strftime("%H:%M")
        for index, shift in enumerate(self.shifts):
            start = str(shift.get("start", "00:00"))
            end = str(shift.get("end", "23:59"))
            if start <= now <= end:
                return f"{index}-{start}-{end}"
        return "default"

    def _record_reset(self, period: str, value: int) -> None:
        if value <= 0:
            return
        path = self.checknum_dir / "check_result_num.txt"
        line = f"{date.today().isoformat()},{period},{value}\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(line)
