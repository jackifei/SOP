from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..services.dashboard_service import DashboardService, DashboardSnapshot
from ..widgets import CameraViewWidget, StatCard

if __package__ in (None, ""):
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.pages.base_page import BasePage
else:
    from .base_page import BasePage


class RunDashboardPage(BasePage):
    """运行看板页面。

    左侧显示相机图像与 ROI，右侧显示当前模板对应的流程步骤状态；
    顶部展示 OK/NG、日/周/月统计和 OK 完成率。
    """

    dashboard_full_status_changed = pyqtSignal(dict)
    template_changed = pyqtSignal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "运行看板",
            "实时查看当前模板、相机画面、流程步骤状态和生产统计。",
            parent,
        )
        self.service = DashboardService()
        self.current_template_name = "默认产品A"
        self.current_steps = []
        self._build_ui()
        self._load_dashboard(self.current_template_name)

    def _build_ui(self) -> None:
        self.add_to_content(self._build_dashboard_status_group())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(5)
        splitter.addWidget(self._build_camera_area())
        splitter.addWidget(self._build_step_area())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([820, 560])
        self.add_to_content(splitter, stretch=1)

    def _build_dashboard_status_group(self) -> QGroupBox:
        group = QGroupBox("看板统计")
        stats_row = QHBoxLayout()
        stats_row.setSpacing(8)

        stats_row.addWidget(QLabel("当前模板"))
        self.template_combo = QComboBox()
        self.template_combo.addItems(list(self.service.TEMPLATES.keys()))
        self.template_combo.setStyleSheet(
            "QComboBox { background-color: #123a56; color: #ffffff; border: 2px solid #4ec9b0; border-radius: 4px; padding: 4px 8px; font-weight: 600; }"
        )
        self.template_combo.setMinimumHeight(54)
        self.template_combo.setMaximumHeight(54)
        stats_row.addWidget(self.template_combo)

        self.ok_card = StatCard("OK", "--", compact=True)
        self.ng_card = StatCard("NG", "--", accent="#f48771", compact=True)
        self.today_card = StatCard("日", "--", compact=True)
        self.week_card = StatCard("周", "--", compact=True)
        self.month_card = StatCard("月", "--", compact=True)
        self.rate_card = StatCard("合格率", "--", accent="#dcdcaa", compact=True)
        for card in (
            self.ok_card,
            self.ng_card,
            self.today_card,
            self.week_card,
            self.month_card,
            self.rate_card,
        ):
            stats_row.addWidget(card, 1)
        group.setLayout(stats_row)

        self.template_combo.currentTextChanged.connect(self._on_template_changed)
        return group

    def _build_camera_area(self) -> QGroupBox:
        group = QGroupBox("相机图像显示区")
        layout = QVBoxLayout(group)

        self.camera_view = CameraViewWidget()
        layout.addWidget(self.camera_view, 1)

        self.roi_label = QLabel("ROI：--")
        self.roi_label.setObjectName("pageTip")
        layout.addWidget(self.roi_label)
        return group

    def _build_step_area(self) -> QGroupBox:
        group = QGroupBox("流程步骤状态")
        layout = QVBoxLayout(group)

        hint = QLabel("显示当前模板对应的检测流程简要内容。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self.step_table = QTableWidget(0, 5)
        self.step_table.setHorizontalHeaderLabels(["步骤", "使用 ROI / 标签", "状态", "耗时", "缩略图"])
        header = self.step_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.step_table.setColumnWidth(4, 120)
        self.step_table.verticalHeader().setVisible(False)
        self.step_table.setAlternatingRowColors(True)
        self.step_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.step_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        layout.addWidget(self.step_table, 1)

        control_row = QHBoxLayout()
        self.reset_fault_button = QPushButton("复位故障")
        self.skip_step_button = QPushButton("跳过当前步骤")
        control_row.addWidget(self.reset_fault_button)
        control_row.addWidget(self.skip_step_button)
        control_row.addStretch(1)
        layout.addLayout(control_row)

        self.step_summary_label = QLabel("步骤状态：--")
        self.step_summary_label.setObjectName("pageTip")
        layout.addWidget(self.step_summary_label)

        self.reset_fault_button.clicked.connect(self._reset_fault)
        self.skip_step_button.clicked.connect(self._skip_current_step)
        return group

    def _build_full_status_area(self) -> QGroupBox:
        self.full_status_group = QGroupBox("完整看板状态")
        self.full_status_group.setVisible(True)
        layout = QHBoxLayout(self.full_status_group)

        self.runtime_label = QLabel("运行时长：--")
        self.shift_output_label = QLabel("当班产量：--")
        self.average_cycle_label = QLabel("平均节拍：--")
        self.device_state_label = QLabel("设备状态：--")
        for label in (
            self.runtime_label,
            self.shift_output_label,
            self.average_cycle_label,
            self.device_state_label,
        ):
            layout.addWidget(label)
        layout.addStretch(1)
        return self.full_status_group

    def _on_template_changed(self, name: str) -> None:
        if not name:
            return
        self._load_dashboard(name)

    def _load_dashboard(self, template_name: str) -> None:
        self.current_template_name = template_name
        self.template_changed.emit(template_name)
        self.template_combo.blockSignals(True)
        self.template_combo.setCurrentText(template_name)
        self.template_combo.blockSignals(False)
        self._apply_snapshot(self.service.snapshot(template_name))

    def _apply_snapshot(self, snapshot: DashboardSnapshot) -> None:
        self.current_steps = snapshot.steps
        self.ok_card.set_value(str(snapshot.ok))
        self.ng_card.set_value(str(snapshot.ng))
        self.today_card.set_value(str(snapshot.today))
        self.week_card.set_value(str(snapshot.week))
        self.month_card.set_value(str(snapshot.month))
        self.rate_card.set_value(f"{snapshot.ok_rate:.1f}%")

        self.camera_view.set_status_text(
            f"当前模板：{snapshot.template_name}    等待相机画面"
        )
        self.camera_view.set_rois(snapshot.rois)
        roi_text = "、".join(f"ROI-{i + 1}" for i in range(len(snapshot.rois))) or "无"
        self.roi_label.setText(f"ROI：{roi_text}")

        self._populate_steps(self.current_steps)
        finished = sum(1 for step in self.current_steps if step.status == "已完成")
        self.step_summary_label.setText(
            f"步骤状态：共 {len(self.current_steps)} 步，已完成 {finished} 步"
        )

        self.set_result(
            f"检测结果：OK {snapshot.ok}，NG {snapshot.ng}，"
            f"合格率 {snapshot.ok_rate:.1f}%"
        )
        self.set_tip(
            "操作提示：切换当前模板可更新看板数据和流程步骤状态。"
        )
        self._emit_full_status(snapshot)

    def _emit_full_status(self, snapshot: DashboardSnapshot | None = None) -> None:
        if snapshot is None:
            self.dashboard_full_status_changed.emit({})
            return
        self.dashboard_full_status_changed.emit(
            {
                "runtime": snapshot.runtime,
                "shift_output": str(snapshot.shift_output),
                "average_cycle": snapshot.average_cycle,
                "device_state": snapshot.device_state,
            }
        )

    def publish_full_status(self) -> None:
        self._emit_full_status(self.service.snapshot(self.current_template_name))

    def _populate_steps(self, steps) -> None:
        self.step_table.setRowCount(0)
        for step in steps:
            row = self.step_table.rowCount()
            self.step_table.insertRow(row)

            name_item = QTableWidgetItem(step.name)
            content_item = QTableWidgetItem(f"{step.roi} / {step.label}")
            status_item = QTableWidgetItem(step.status)
            duration_item = QTableWidgetItem(step.duration)

            color = {
                "已完成": Qt.GlobalColor.green,
                "执行中": Qt.GlobalColor.yellow,
                "失败": Qt.GlobalColor.red,
            }.get(step.status)
            if color is not None:
                status_item.setForeground(color)

            for column, item in enumerate(
                [name_item, content_item, status_item, duration_item]
            ):
                self.step_table.setItem(row, column, item)

            thumbnail = QLabel()
            thumbnail.setPixmap(self._make_thumbnail(step.status))
            thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.step_table.setCellWidget(row, 4, thumbnail)
            self.step_table.setRowHeight(row, 70)

    def _make_thumbnail(self, status: str) -> QPixmap:
        pixmap = QPixmap(112, 64)
        pixmap.fill(QColor("#111111"))
        painter = QPainter(pixmap)
        color = {
            "已完成": QColor("#4ec9b0"),
            "执行中": QColor("#dcdcaa"),
            "失败": QColor("#f48771"),
        }.get(status, QColor("#555555"))
        painter.fillRect(6, 6, 100, 52, color)
        painter.setPen(QColor("#ffffff"))
        painter.setFont(QFont("Microsoft YaHei", 9))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, status)
        painter.end()
        return pixmap

    def _reset_fault(self) -> None:
        for step in self.current_steps:
            if step.status in {"失败", "超时"}:
                step.status = "待执行"
                step.duration = "--"
        self._populate_steps(self.current_steps)
        self.set_tip("操作提示：故障状态已复位，相关步骤回到待执行状态。")

    def _skip_current_step(self) -> None:
        row = self.step_table.currentRow()
        if row < 0:
            row = next(
                (
                    index
                    for index, step in enumerate(self.current_steps)
                    if step.status not in {"已完成", "失败"}
                ),
                0,
            )
        if row >= len(self.current_steps):
            return

        box = QMessageBox(self)
        box.setWindowTitle("跳过当前步骤")
        box.setText(f"当前步骤：{self.current_steps[row].name}\n请选择本步通过结果：")
        ok_button = box.addButton("OK 通过", QMessageBox.ButtonRole.AcceptRole)
        ng_button = box.addButton("NG 通过", QMessageBox.ButtonRole.RejectRole)
        box.exec()

        if box.clickedButton() is ok_button:
            self.current_steps[row].status = "已完成"
            self.current_steps[row].duration = "0.00 s"
            if row + 1 < len(self.current_steps):
                self.current_steps[row + 1].status = "执行中"
        elif box.clickedButton() is ng_button:
            self.current_steps[row].status = "失败"
            self.current_steps[row].duration = "--"

        self._populate_steps(self.current_steps)
        finished = sum(1 for step in self.current_steps if step.status == "已完成")
        self.step_summary_label.setText(
            f"步骤状态：共 {len(self.current_steps)} 步，已完成 {finished} 步"
        )

if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].RunDashboardPage))
