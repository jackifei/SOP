from __future__ import annotations

from copy import deepcopy

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
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
    """ROI 大图编辑弹窗。"""

    def __init__(
        self,
        rois: list[dict],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("ROI 创建与编辑")
        self.resize(980, 680)
        self._updating = False
        self._rois = deepcopy(rois)
        self._build_ui()
        self._populate_table()
        self.canvas.set_rois(self._rois)

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        hint = QLabel("在大图中点击 ROI 可选中；双击空白处自动新建 ROI。")
        root.addWidget(hint)

        content = QHBoxLayout()
        self.canvas = RoiCanvas()
        content.addWidget(self.canvas, 3)

        table_area = QVBoxLayout()
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["名称", "X", "Y", "宽", "高"])
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table_area.addWidget(self.table, 1)

        buttons = QHBoxLayout()
        add_button = QPushButton("添加 ROI")
        delete_button = QPushButton("删除选中")
        buttons.addWidget(add_button)
        buttons.addWidget(delete_button)
        table_area.addLayout(buttons)
        content.addLayout(table_area, 2)
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
        apply_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        self.canvas.selection_changed.connect(self._on_canvas_selection)
        self.canvas.add_requested.connect(self._add_roi_at)
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
        values = [
            str(roi.get("name", "")),
            str(roi.get("x", 0)),
            str(roi.get("y", 0)),
            str(roi.get("w", 0)),
            str(roi.get("h", 0)),
        ]
        for column, value in enumerate(values):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, column, item)

    def _add_roi(self) -> None:
        self._add_roi_at(40 + len(self._rois) * 20, 40 + len(self._rois) * 20)

    def _add_roi_at(self, x: int, y: int) -> None:
        self._rois.append(
            {
                "name": f"ROI-{len(self._rois) + 1}",
                "x": max(0, x),
                "y": max(0, y),
                "w": 160,
                "h": 120,
            }
        )
        self._populate_table()
        self.canvas.set_rois(self._rois)

    def _delete_selected_roi(self) -> None:
        row = self.table.currentRow()
        if row < 0 or row >= len(self._rois):
            return
        self._rois.pop(row)
        self._populate_table()
        self.canvas.set_rois(self._rois)

    def _on_canvas_selection(self, index: int) -> None:
        if index < 0 or index >= self.table.rowCount():
            self.table.clearSelection()
            return
        self.table.selectRow(index)

    def _on_table_selection(self) -> None:
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        self.canvas.selected_index = rows[0].row()
        self.canvas.update()

    def _on_table_changed(self, item: QTableWidgetItem) -> None:
        if self._updating:
            return
        row = item.row()
        column = item.column()
        if row >= len(self._rois):
            return
        key = ["name", "x", "y", "w", "h"][column]
        if key == "name":
            self._rois[row][key] = item.text().strip()
        else:
            try:
                self._rois[row][key] = int(item.text())
            except ValueError:
                self._rois[row][key] = 0
        self.canvas.set_rois(self._rois)
