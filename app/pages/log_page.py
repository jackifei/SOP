from __future__ import annotations

from PyQt6.QtCore import QDateTime, Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.pages.base_page import BasePage
    from app.services.config_service import ConfigService
else:
    from .base_page import BasePage
    from ..services.config_service import ConfigService


class LogPage(BasePage):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "日志",
            "查看系统运行日志，支持按级别筛选。",
            parent,
        )
        self.config_service = ConfigService()
        self._build_ui()
        self._append_demo_logs()
        self.set_result("检测结果：已加载演示日志")
        self.set_tip("操作提示：可按级别筛选，后续可接入文件或数据库日志源。")

    def _build_ui(self) -> None:
        group = QGroupBox("运行日志")
        layout = QVBoxLayout(group)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("级别"))

        self.level_combo = QComboBox()
        self.level_combo.addItems(["全部", "DEBUG", "INFO", "WARN", "ERROR"])
        toolbar.addWidget(self.level_combo)

        self.add_test_log_button = QPushButton("添加测试日志")
        self.clear_button = QPushButton("清空日志")
        self.export_button = QPushButton("导出 CSV")
        self.save_filter_button = QPushButton("保存筛选")
        toolbar.addWidget(self.add_test_log_button)
        toolbar.addWidget(self.clear_button)
        toolbar.addWidget(self.export_button)
        toolbar.addWidget(self.save_filter_button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.log_table = QTableWidget(0, 4)
        self.log_table.setHorizontalHeaderLabels(["时间", "级别", "来源", "消息"])
        self.log_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.log_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setAlternatingRowColors(True)
        self.log_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.log_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.log_table, 1)

        self.add_to_content(group, stretch=1)

        self.level_combo.currentTextChanged.connect(self._apply_filter)
        self.add_test_log_button.clicked.connect(self._add_random_log)
        self.clear_button.clicked.connect(lambda: self.log_table.setRowCount(0))
        self.export_button.clicked.connect(self._export_placeholder)
        self.save_filter_button.clicked.connect(self._save_filter_config)

    def _append_demo_logs(self) -> None:
        samples = [
            ("INFO", "app", "应用启动"),
            ("INFO", "camera", "相机初始化完成"),
            ("WARN", "device", "设备心跳超时一次"),
            ("ERROR", "camera", "相机取流失败：timeout"),
            ("INFO", "flow", "检测流程已加载"),
        ]
        for level, source, message in samples:
            self._append_log(level, source, message)

    def _append_log(self, level: str, source: str, message: str) -> None:
        row = self.log_table.rowCount()
        self.log_table.insertRow(row)

        time_item = QTableWidgetItem(QDateTime.currentDateTime().toString("yyyy-MM-dd HH:mm:ss"))
        level_item = QTableWidgetItem(level)
        source_item = QTableWidgetItem(source)
        message_item = QTableWidgetItem(message)

        if level == "ERROR":
            level_item.setForeground(Qt.GlobalColor.red)
        elif level == "WARN":
            level_item.setForeground(Qt.GlobalColor.yellow)
        elif level == "INFO":
            level_item.setForeground(Qt.GlobalColor.green)

        for column, item in enumerate([time_item, level_item, source_item, message_item]):
            self.log_table.setItem(row, column, item)
        self.log_table.scrollToBottom()

    def _apply_filter(self, level: str) -> None:
        for row in range(self.log_table.rowCount()):
            item = self.log_table.item(row, 1)
            match = level == "全部" or (item is not None and item.text() == level)
            self.log_table.setRowHidden(row, not match)

    def _add_random_log(self) -> None:
        levels = ["DEBUG", "INFO", "WARN", "ERROR"]
        selected = self.level_combo.currentText()
        level = selected if selected != "全部" else "INFO"
        if level not in levels:
            level = "INFO"
        self._append_log(level, "demo", "这是一条测试日志")
        self._apply_filter(self.level_combo.currentText())

    def _export_placeholder(self) -> None:
        # 插入点：将当前日志表接入 csv/xlsx 导出或远程日志服务。
        self._append_log("INFO", "log", "导出 CSV：demo 占位，可在后续接入实际导出逻辑")
        self._apply_filter(self.level_combo.currentText())

    def _save_filter_config(self) -> None:
        self.config_service.save_page_config(
            "log",
            {"level_filter": self.level_combo.currentText()},
        )
        self.set_tip("操作提示：日志筛选条件已保存到 config/log.yaml。")

    def auto_save_config(self) -> None:
        self._save_filter_config()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].LogPage))
