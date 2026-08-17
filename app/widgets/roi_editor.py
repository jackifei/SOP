from __future__ import annotations

from copy import deepcopy

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .roi_canvas import RoiCanvas


class RoiEditorDialog(QDialog):
    """ROI 大图编辑弹窗。

    支持圆形 ROI 和旋转矩形 ROI，支持中心点拖拽与矩形旋转。
    """

    def __init__(
        self,
        rois: list[dict],
        image: QPixmap | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("ROI 创建与编辑")
        self.resize(1020, 700)
        self._updating = False
        self._rois = deepcopy(rois)
        self._image = image
        self._build_ui()
        self._populate_table()
        self.canvas.set_image(self._image)
        self.canvas.set_rois(self._rois)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        hint = QLabel("双击空白处新建 ROI；拖动中心点可移动；旋转矩形可旋转。")
        root.addWidget(hint)

        content = QHBoxLayout()
        self.canvas = RoiCanvas()
        content.addWidget(self.canvas, 3)

        side = QVBoxLayout()
        shape_row = QHBoxLayout()
        shape_row.addWidget(QLabel("绘制类型"))
        self.shape_combo = QComboBox()
        self.shape_combo.addItems(["旋转矩形", "圆形"])
        shape_row.addWidget(self.shape_combo)
        side.addLayout(shape_row)

        cross_row = QHBoxLayout()
        self.show_cross_check = QCheckBox("显示十字线")
        self.show_cross_check.setChecked(False)
        cross_row.addWidget(self.show_cross_check)
        side.addLayout(cross_row)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["名称", "类型", "中心X", "中心Y", "宽/半径", "高", "角度"]
        )
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        side.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        add_button = QPushButton("添加 ROI")
        delete_button = QPushButton("删除选中")
        rotate_ccw_button = QPushButton("反转")
        rotate_cw_button = QPushButton("正转")
        self.rotation_step_combo = QComboBox()
        self.rotation_step_combo.addItems(["精细 1°", "中等 5°", "最大 15°"])
        buttons.addWidget(add_button)
        buttons.addWidget(delete_button)
        buttons.addWidget(rotate_ccw_button)
        buttons.addWidget(rotate_cw_button)
        buttons.addWidget(self.rotation_step_combo)
        side.addLayout(buttons)
        content.addLayout(side, 2)
        root.addLayout(content, 1)

        bottom = QHBoxLayout()
        bottom.addStretch(1)
        apply_button = QPushButton("应用")
        cancel_button = QPushButton("取消")
        bottom.addWidget(apply_button)
        bottom.addWidget(cancel_button)
        root.addLayout(bottom)

        add_button.clicked.connect(lambda: self._add_roi())
        delete_button.clicked.connect(self._delete_selected_roi)
        rotate_ccw_button.clicked.connect(lambda: self._rotate_selected_rect(-1))
        rotate_cw_button.clicked.connect(lambda: self._rotate_selected_rect(1))
        self.show_cross_check.toggled.connect(self.canvas.set_show_cross)
        apply_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        self.canvas.selection_changed.connect(self._on_canvas_selection)
        self.canvas.add_requested.connect(self._add_roi_at)
        self.canvas.roi_updated.connect(self._on_canvas_roi_updated)
        self.table.itemChanged.connect(self._on_table_changed)
        self.table.itemSelectionChanged.connect(self._on_table_selection)

    def selected_rois(self) -> list[dict]:
        return self._rois

    def _populate_table(self) -> None:
        self._updating = True
        self.table.setRowCount(0)
        for roi in self._rois:
            self._append_roi_row(roi)
        self._updating = False

    def _append_roi_row(self, roi: dict) -> None:
        row = self.table.rowCount()
        self.table.insertRow(row)
        shape = roi.get("shape", "rect")
        values = [
            roi.get("name", ""),
            "圆形" if shape == "circle" else "旋转矩形",
            str(roi.get("center_x", 0)),
            str(roi.get("center_y", 0)),
            str(roi.get("radius", 30) if shape == "circle" else roi.get("width", 160)),
            "0" if shape == "circle" else str(roi.get("height", 120)),
            "0" if shape == "circle" else str(roi.get("angle", 0)),
        ]
        for column, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, column, item)

    def _add_roi(self) -> None:
        self._add_roi_at(80 + len(self._rois) * 20, 80 + len(self._rois) * 20)

    def _add_roi_at(self, x: float, y: float) -> None:
        shape = "circle" if self.shape_combo.currentText() == "圆形" else "rect"
        if shape == "circle":
            roi = {
                "name": f"ROI-{len(self._rois) + 1}",
                "shape": "circle",
                "center_x": round(x, 2),
                "center_y": round(y, 2),
                "radius": 60,
            }
        else:
            roi = {
                "name": f"ROI-{len(self._rois) + 1}",
                "shape": "rect",
                "center_x": round(x, 2),
                "center_y": round(y, 2),
                "width": 180,
                "height": 120,
                "angle": 0,
            }
        self._rois.append(roi)
        self._populate_table()
        self.canvas.set_rois(self._rois)

    def _delete_selected_roi(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rois):
            return
        self._rois.pop(row)
        self._populate_table()
        self.canvas.set_rois(self._rois)

    def _rotate_selected_rect(self, direction: int) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rois):
            return
        roi = self._rois[row]
        if roi.get("shape", "rect") != "rect":
            return
        step_text = self.rotation_step_combo.currentText()
        step = 15.0 if step_text.startswith("最大") else (5.0 if step_text.startswith("中等") else 1.0)
        roi["angle"] = float(roi.get("angle", 0)) + direction * step
        self._populate_table()
        self.canvas.set_rois(self._rois)
        self.canvas.selected_index = row
        self.canvas.update()
        self.table.selectRow(row)

    def _on_canvas_selection(self, index: int) -> None:
        if index < 0 or index >= self.table.rowCount():
            self.table.clearSelection()
            return
        self.table.clearSelection()
        self.table.selectRow(index)

    def _on_table_selection(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        self.canvas.selected_index = rows[0].row()
        self.canvas.update()

    def _on_canvas_roi_updated(self, index: int) -> None:
        if index < 0 or index >= len(self._rois):
            return
        roi = self._rois[index]
        self._updating = True
        self.table.item(index, 2).setText(str(roi.get("center_x", 0)))
        self.table.item(index, 3).setText(str(roi.get("center_y", 0)))
        if roi.get("shape") == "circle":
            self.table.item(index, 4).setText(str(roi.get("radius", 30)))
            self.table.item(index, 5).setText("0")
            self.table.item(index, 6).setText("0")
        else:
            self.table.item(index, 4).setText(str(roi.get("width", 160)))
            self.table.item(index, 5).setText(str(roi.get("height", 120)))
            self.table.item(index, 6).setText(str(roi.get("angle", 0)))
        self._updating = False

    def _on_table_changed(self, item: QTableWidgetItem) -> None:
        if self._updating:
            return
        row = item.row()
        column = item.column()
        if row >= len(self._rois):
            return
        roi = self._rois[row]
        text = item.text().strip()
        if column == 0:
            roi["name"] = text
        elif column == 1:
            roi["shape"] = "circle" if text == "圆形" else "rect"
            if roi["shape"] == "circle" and "radius" not in roi:
                roi["radius"] = 60
            if roi["shape"] == "rect" and "width" not in roi:
                roi["width"] = 180
                roi["height"] = 120
                roi["angle"] = 0
        else:
            key = ["", "", "center_x", "center_y", "width_or_radius", "height", "angle"][column]
            try:
                value = float(text)
            except ValueError:
                value = 0.0
            if key == "center_x":
                roi["center_x"] = value
            elif key == "center_y":
                roi["center_y"] = value
            elif key == "width_or_radius":
                if roi.get("shape") == "circle":
                    roi["radius"] = value
                else:
                    roi["width"] = value
            elif key == "height":
                if roi.get("shape") != "circle":
                    roi["height"] = value
            elif key == "angle":
                if roi.get("shape") != "circle":
                    roi["angle"] = value
        self.canvas.set_rois(self._rois)
