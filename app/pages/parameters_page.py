from __future__ import annotations

from PyQt6.QtCore import QTime, Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.pages.base_page import BasePage
    from app.services.config_service import ConfigService
    from app.services.production_stats_service import ProductionStatsService
else:
    from .base_page import BasePage
    from ..services.config_service import ConfigService
    from ..services.production_stats_service import ProductionStatsService


class ParametersPage(BasePage):
    """系统参数页。

    相机参数已迁移到相机管理页，检测参数已迁移到流程编辑页，
    此处只保留系统级参数。
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "参数",
            "系统级参数设置。相机参数和检测参数已迁移到各自界面。",
            parent,
        )
        self.config_service = ConfigService()
        self.stats_service = ProductionStatsService()
        self._build_ui()
        self._load_config()
        self.set_result("检测结果：系统参数已加载")
        self.set_tip("操作提示：修改后点击“保存系统参数”写入 config/system.yaml。")

    def _build_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(12)

        system_group = QGroupBox("系统参数")
        form = QFormLayout(system_group)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["简体中文", "English"])

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARN", "ERROR"])
        self.log_level_combo.setCurrentText("INFO")

        self.auto_save_check = QCheckBox("启用自动保存")
        self.auto_save_check.setChecked(True)

        form.addRow("界面语言", self.language_combo)
        form.addRow("日志级别", self.log_level_combo)
        form.addRow("", self.auto_save_check)
        layout.addWidget(system_group)

        storage_group = QGroupBox("存储路径")
        storage_form = QFormLayout(storage_group)
        storage_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.result_dir_edit = QLineEdit()
        self.result_dir_edit.setPlaceholderText("选择检测结果存储目录")
        self.result_dir_button = QPushButton("选择")
        result_row = QWidget()
        result_layout = QHBoxLayout(result_row)
        result_layout.setContentsMargins(0, 0, 0, 0)
        result_layout.addWidget(self.result_dir_edit, 1)
        result_layout.addWidget(self.result_dir_button)

        self.data_dir_edit = QLineEdit()
        self.data_dir_edit.setPlaceholderText("选择数据存储目录")
        self.data_dir_button = QPushButton("选择")
        data_row = QWidget()
        data_layout = QHBoxLayout(data_row)
        data_layout.setContentsMargins(0, 0, 0, 0)
        data_layout.addWidget(self.data_dir_edit, 1)
        data_layout.addWidget(self.data_dir_button)

        storage_form.addRow("检测结果目录", result_row)
        storage_form.addRow("数据存储目录", data_row)
        layout.addWidget(storage_group)

        shift_group = QGroupBox("班次设置")
        shift_layout = QVBoxLayout(shift_group)
        shift_hint = QLabel("最多 6 个班，时间格式 HH:MM。")
        shift_layout.addWidget(shift_hint)

        count_mode_row = QHBoxLayout()
        count_mode_row.addWidget(QLabel("计数方式"))
        self.count_mode_combo = QComboBox()
        self.count_mode_combo.addItems(["日计数", "班计数"])
        self.count_mode_combo.setCurrentText(self.stats_service.count_mode)
        count_mode_row.addWidget(self.count_mode_combo)
        count_mode_row.addStretch(1)
        shift_layout.addLayout(count_mode_row)

        self.shift_table = QTableWidget(6, 3)
        self.shift_table.setHorizontalHeaderLabels(["班次", "开始时间", "结束时间"])
        self.shift_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.shift_table.verticalHeader().setVisible(False)
        for row in range(6):
            self.shift_table.setItem(row, 0, QTableWidgetItem(f"班次 {row + 1}"))
            start_edit = QTimeEdit(QTime(0, 0))
            start_edit.setDisplayFormat("HH:mm")
            end_edit = QTimeEdit(QTime(23, 59))
            end_edit.setDisplayFormat("HH:mm")
            self.shift_table.setCellWidget(row, 1, start_edit)
            self.shift_table.setCellWidget(row, 2, end_edit)
        shift_layout.addWidget(self.shift_table)
        layout.addWidget(shift_group)

        self.save_button = QPushButton("保存系统参数")
        layout.addWidget(self.save_button)
        layout.addStretch(1)

        scroll.setWidget(container)
        self.add_to_content(scroll, stretch=1)

        self.save_button.clicked.connect(self._save_config)
        self.result_dir_button.clicked.connect(self._choose_result_dir)
        self.data_dir_button.clicked.connect(self._choose_data_dir)
        self._load_shift_config()

    def _save_config(self) -> None:
        self.config_service.save_page_config(
            "system",
            {
                "language": self.language_combo.currentText(),
                "log_level": self.log_level_combo.currentText(),
                "auto_save": self.auto_save_check.isChecked(),
                "result_dir": self.result_dir_edit.text(),
                "data_dir": self.data_dir_edit.text(),
            },
        )
        self._save_shift_config()
        self.set_tip("操作提示：系统参数已保存到 config/system.yaml。")

    def _load_config(self) -> None:
        data = self.config_service.load_page_config("system")
        if not data:
            return
        self.language_combo.setCurrentText(str(data.get("language", self.language_combo.currentText())))
        self.log_level_combo.setCurrentText(str(data.get("log_level", self.log_level_combo.currentText())))
        self.auto_save_check.setChecked(bool(data.get("auto_save", self.auto_save_check.isChecked())))
        self.result_dir_edit.setText(str(data.get("result_dir", "")))
        self.data_dir_edit.setText(str(data.get("data_dir", "")))

    def _collect_shifts(self) -> list[dict]:
        shifts = []
        for row in range(self.shift_table.rowCount()):
            name_item = self.shift_table.item(row, 0)
            start_widget = self.shift_table.cellWidget(row, 1)
            end_widget = self.shift_table.cellWidget(row, 2)
            name = name_item.text().strip() if name_item else ""
            start = start_widget.time().toString("HH:mm") if isinstance(start_widget, QTimeEdit) else ""
            end = end_widget.time().toString("HH:mm") if isinstance(end_widget, QTimeEdit) else ""
            if start and end and (start != "00:00" or end != "23:59"):
                shifts.append({"name": name or f"班次 {row + 1}", "start": start, "end": end})
        return shifts

    def _save_shift_config(self) -> None:
        self.config_service.save_page_config("shifts", {"shifts": self._collect_shifts()})
        self.stats_service.set_count_mode(self.count_mode_combo.currentText())

    def _load_shift_config(self) -> None:
        data = self.config_service.load_page_config("shifts")
        shifts = data.get("shifts", [])
        for row, shift in enumerate(shifts[:6]):
            self.shift_table.item(row, 0).setText(str(shift.get("name", f"班次 {row + 1}")))
            start = QTime.fromString(str(shift.get("start", "00:00")), "HH:mm")
            end = QTime.fromString(str(shift.get("end", "23:59")), "HH:mm")
            if start.isValid():
                self.shift_table.cellWidget(row, 1).setTime(start)
            if end.isValid():
                self.shift_table.cellWidget(row, 2).setTime(end)

    def _choose_result_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择检测结果存储目录")
        if directory:
            self.result_dir_edit.setText(directory)

    def _choose_data_dir(self) -> None:
        directory = QFileDialog.getExistingDirectory(self, "选择数据存储目录")
        if directory:
            self.data_dir_edit.setText(directory)

    def auto_save_config(self) -> None:
        self._save_config()


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].ParametersPage))
