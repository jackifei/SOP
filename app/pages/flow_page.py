from __future__ import annotations

from copy import deepcopy

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QDialog,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
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
    from app.widgets import RoiCanvas, RoiEditorDialog
else:
    from .base_page import BasePage
    from ..services.config_service import ConfigService
    from ..widgets import RoiCanvas, RoiEditorDialog


def _default_template(name: str) -> dict:
    """生成默认模板数据。实际项目可替换为配置文件或数据库加载。"""
    return {
        "name": name,
        "model_file": "",
        "labels": ["person", "helmet", "glove", "mask", "defect"],
        "steps": [
            {
                "name": "第一次检测",
                "roi": "ROI-1",
                "label": "person",
                "confidence": 0.55,
                "detection_count": 20,
                "use_gesture": False,
                "gesture": "无",
                "enabled": True,
            },
            {
                "name": "第二次检测",
                "roi": "ROI-2",
                "label": "defect",
                "confidence": 0.45,
                "detection_count": 30,
                "use_gesture": True,
                "gesture": "OK",
                "enabled": True,
            },
        ],
        "rois": [
            {"name": "ROI-1", "x": 50, "y": 45, "w": 200, "h": 150},
            {"name": "ROI-2", "x": 330, "y": 90, "w": 220, "h": 160},
        ],
    }


class FlowPage(BasePage):
    """流程编辑页。

    支持产品模板管理、模型/中文标签映射、检测流程步骤配置和手势选项。
    """

    DEFAULT_ROIS = ["全图", "ROI-1", "ROI-2"]
    GESTURES = ["无", "OK", "NG", "握拳", "手掌", "拇指向上", "拇指向下"]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            "流程编辑",
            "创建产品模板，配置模型、标签中文名、ROI 流程及检测参数。",
            parent,
        )
        self.templates: dict[str, dict] = {
            "默认产品A": _default_template("默认产品A"),
            "产品B": _default_template("产品B"),
        }
        self.config_service = ConfigService()
        self.current_template_name = ""
        self._build_ui()
        self._load_template("默认产品A")

    def _build_ui(self) -> None:
        top_splitter = QSplitter(Qt.Orientation.Horizontal)
        top_splitter.setChildrenCollapsible(False)
        top_splitter.setHandleWidth(5)
        self.roi_panel = self._build_roi_area()
        self.roi_panel.setMinimumWidth(320)
        top_splitter.addWidget(self.roi_panel)
        self.label_panel = self._build_combined_area()
        self.label_panel.setMinimumWidth(380)
        top_splitter.addWidget(self.label_panel)
        top_splitter.setStretchFactor(0, 1)
        top_splitter.setStretchFactor(1, 0)
        top_splitter.setSizes([900, 380])

        self.flow_panel = self._build_flow_area()
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        main_splitter.setChildrenCollapsible(False)
        main_splitter.setHandleWidth(5)
        main_splitter.addWidget(top_splitter)
        main_splitter.addWidget(self.flow_panel)
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 1)
        main_splitter.setSizes([360, 420])

        self.add_to_content(main_splitter, stretch=1)

    def _build_roi_area(self) -> QGroupBox:
        group = QGroupBox("ROI 配置区")
        layout = QVBoxLayout(group)

        self.roi_canvas = RoiCanvas()
        layout.addWidget(self.roi_canvas, 1)

        roi_hint = QLabel("点击缩略图可打开大图进行 ROI 创建与编辑。")
        roi_hint.setWordWrap(True)
        layout.addWidget(roi_hint)

        self.edit_roi_button = QPushButton("编辑 ROI")
        layout.addWidget(self.edit_roi_button)
        self.edit_roi_button.clicked.connect(self._open_roi_editor)
        return group

    def _build_combined_area(self) -> QGroupBox:
        group = QGroupBox("产品模板 / 模型标签")
        layout = QVBoxLayout(group)

        template_top = QHBoxLayout()
        template_top.addWidget(QLabel("当前模板"))
        self.template_combo = QComboBox()
        self.template_combo.addItems(list(self.templates.keys()))
        template_top.addWidget(self.template_combo, 1)
        self.new_template_button = QPushButton("新建模板")
        self.edit_template_button = QPushButton("编辑模板")
        self.delete_template_button = QPushButton("删除模板")
        self.save_template_button = QPushButton("保存当前")
        template_top.addWidget(self.new_template_button)
        template_top.addWidget(self.edit_template_button)
        template_top.addWidget(self.delete_template_button)
        template_top.addWidget(self.save_template_button)
        layout.addLayout(template_top)

        self.model_file_label = QLabel("模型文件：未加载")
        self.model_file_label.setStyleSheet("color: #9d9d9d;")
        layout.addWidget(self.model_file_label)

        label_buttons = QHBoxLayout()
        self.load_model_button = QPushButton("加载模型")
        self.load_labels_button = QPushButton("加载标签")
        self.clear_labels_button = QPushButton("清空")
        label_buttons.addWidget(self.load_model_button)
        label_buttons.addWidget(self.load_labels_button)
        label_buttons.addWidget(self.clear_labels_button)
        label_buttons.addStretch(1)
        layout.addLayout(label_buttons)

        self.label_table = QTableWidget(0, 1)
        self.label_table.setHorizontalHeaderLabels(["标签名称"])
        self.label_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.label_table.verticalHeader().setVisible(True)
        self.label_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.label_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.label_table, 1)

        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        self.new_template_button.clicked.connect(self._new_template)
        self.edit_template_button.clicked.connect(self._edit_template)
        self.delete_template_button.clicked.connect(self._delete_template)
        self.save_template_button.clicked.connect(self._save_current_template)
        self.load_model_button.clicked.connect(self._load_model)
        self.load_labels_button.clicked.connect(self._load_labels)
        self.clear_labels_button.clicked.connect(self._clear_labels)
        return group

    def _build_template_area(self) -> QGroupBox:
        group = QGroupBox("产品模板 / 配方")
        layout = QVBoxLayout(group)

        top = QHBoxLayout()
        top.addWidget(QLabel("当前模板"))
        self.template_combo = QComboBox()
        self.template_combo.addItems(list(self.templates.keys()))
        top.addWidget(self.template_combo, 1)

        self.new_template_button = QPushButton("新建模板")
        self.edit_template_button = QPushButton("编辑模板")
        self.delete_template_button = QPushButton("删除模板")
        self.save_template_button = QPushButton("保存当前")
        top.addWidget(self.new_template_button)
        top.addWidget(self.edit_template_button)
        top.addWidget(self.delete_template_button)
        top.addWidget(self.save_template_button)
        layout.addLayout(top)

        self.model_file_label = QLabel("模型文件：未加载")
        self.model_file_label.setStyleSheet("color: #9d9d9d;")
        layout.addWidget(self.model_file_label)

        params = QHBoxLayout()
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.01, 1.0)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.setValue(0.5)

        self.detection_count_spin = QSpinBox()
        self.detection_count_spin.setRange(1, 1000)
        self.detection_count_spin.setValue(20)

        self.use_gesture_check = QCheckBox("使用手势")
        self.gesture_combo = QComboBox()
        self.gesture_combo.addItems(self.GESTURES)
        self.gesture_combo.setEnabled(False)

        params.addWidget(QLabel("置信度"))
        params.addWidget(self.confidence_spin)
        params.addWidget(QLabel("检测数量"))
        params.addWidget(self.detection_count_spin)
        params.addWidget(self.use_gesture_check)
        params.addWidget(QLabel("手势姿势"))
        params.addWidget(self.gesture_combo)
        params.addStretch(1)
        layout.addLayout(params)

        self.template_combo.currentIndexChanged.connect(self._on_template_changed)
        self.new_template_button.clicked.connect(self._new_template)
        self.edit_template_button.clicked.connect(self._edit_template)
        self.delete_template_button.clicked.connect(self._delete_template)
        self.save_template_button.clicked.connect(self._save_current_template)
        self.use_gesture_check.toggled.connect(self.gesture_combo.setEnabled)
        return group

    def _build_label_area(self) -> QGroupBox:
        group = QGroupBox("模型标签")
        layout = QVBoxLayout(group)

        buttons = QHBoxLayout()
        self.load_model_button = QPushButton("加载模型")
        self.load_labels_button = QPushButton("加载标签")
        self.clear_labels_button = QPushButton("清空")
        buttons.addWidget(self.load_model_button)
        buttons.addWidget(self.load_labels_button)
        buttons.addWidget(self.clear_labels_button)
        buttons.addStretch(1)
        layout.addLayout(buttons)

        self.label_table = QTableWidget(0, 2)
        self.label_table.setHorizontalHeaderLabels(["英文名称", "中文名称"])
        self.label_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.label_table.verticalHeader().setVisible(True)
        self.label_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.label_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self.label_table, 1)

        self.load_model_button.clicked.connect(self._load_model)
        self.load_labels_button.clicked.connect(self._load_labels)
        self.clear_labels_button.clicked.connect(self._clear_labels)
        return group

    def _build_flow_area(self) -> QGroupBox:
        group = QGroupBox("检测流程配置")
        layout = QVBoxLayout(group)

        hint = QLabel("每一行代表一个检测阶段；标签选择来自左侧英文标签。")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        toolbar = QHBoxLayout()
        self.toggle_label_button = QPushButton("隐藏模板/标签栏")
        add_step = QPushButton("添加步骤")
        delete_step = QPushButton("删除选中")
        move_up = QPushButton("上移")
        move_down = QPushButton("下移")
        single_run = QPushButton("单次执行")
        toolbar.addWidget(self.toggle_label_button)
        toolbar.addSpacing(12)
        toolbar.addWidget(add_step)
        toolbar.addWidget(delete_step)
        toolbar.addWidget(move_up)
        toolbar.addWidget(move_down)
        toolbar.addWidget(single_run)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.flow_table = QTableWidget(0, 8)
        self.flow_table.setHorizontalHeaderLabels(
            ["步骤名称", "使用 ROI", "使用标签", "置信度分数", "检测数量", "使用手势", "手势姿势", "启用"]
        )
        header = self.flow_table.horizontalHeader()
        for column in range(self.flow_table.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(70)
        header.setDefaultSectionSize(120)
        self.flow_table.verticalHeader().setVisible(False)
        self.flow_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.flow_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        layout.addWidget(self.flow_table, 1)

        self.toggle_label_button.clicked.connect(self._toggle_label_panel)
        add_step.clicked.connect(lambda: self._add_step())
        delete_step.clicked.connect(self._delete_selected_step)
        move_up.clicked.connect(lambda: self._move_step(-1))
        move_down.clicked.connect(lambda: self._move_step(1))
        single_run.clicked.connect(self._execute_selected_step)
        return group

    def _load_template(self, name: str) -> None:
        template = self.templates.get(name)
        if template is None:
            return
        self.current_template_name = name
        self.template_combo.blockSignals(True)
        self.template_combo.setCurrentText(name)
        self.template_combo.blockSignals(False)

        self.model_file_label.setText(f"模型文件：{template.get('model_file') or '未加载'}")
        self.roi_canvas.set_rois(deepcopy(template.get("rois", [])))

        self._populate_labels(template.get("labels", []))
        self.flow_table.setRowCount(0)
        for step in template.get("steps", []):
            self._add_step(
                step.get("name", "新步骤"),
                step.get("roi", "全图"),
                step.get("label", ""),
                float(step.get("confidence", 0.5)),
                int(step.get("detection_count", 20)),
                bool(step.get("use_gesture", False)),
                str(step.get("gesture", "无")),
                bool(step.get("enabled", True)),
            )

        self.set_result(f"检测结果：模板「{name}」已加载")
        self.set_tip("操作提示：先选择或新建模板，再配置模型、标签和检测步骤。")

    def _on_template_changed(self) -> None:
        name = self.template_combo.currentText()
        if not name or name == self.current_template_name:
            return
        self._save_current_template()
        self._load_template(name)

    def _new_template(self) -> None:
        name, ok = QInputDialog.getText(self, "新建模板", "请输入模板名称：")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self.templates:
            QMessageBox.warning(self, "提示", "模板名称已存在。")
            return
        self._save_current_template()
        self.templates[name] = _default_template(name)
        self.template_combo.blockSignals(True)
        self.template_combo.addItem(name)
        self.template_combo.blockSignals(False)
        self._load_template(name)

    def _edit_template(self) -> None:
        name = self.template_combo.currentText()
        new_name, ok = QInputDialog.getText(self, "编辑模板", "模板名称：", text=name)
        if not ok or not new_name.strip():
            return
        new_name = new_name.strip()
        if new_name != name and new_name in self.templates:
            QMessageBox.warning(self, "提示", "模板名称已存在。")
            return

        model_file, _ = QFileDialog.getOpenFileName(
            self,
            "选择模型文件",
            "",
            "模型文件 (*.pt *.pth *.onnx *.engine *.bin);;所有文件 (*.*)",
        )
        self._save_current_template()
        data = self.templates.pop(name)
        data["name"] = new_name
        if model_file:
            data["model_file"] = model_file
        self.templates[new_name] = data

        self.template_combo.blockSignals(True)
        index = self.template_combo.findText(name)
        if index >= 0:
            self.template_combo.setItemText(index, new_name)
        self.template_combo.blockSignals(False)
        self._load_template(new_name)

    def _delete_template(self) -> None:
        if len(self.templates) <= 1:
            QMessageBox.information(self, "提示", "至少需要保留一个产品模板。")
            return
        name = self.template_combo.currentText()
        answer = QMessageBox.question(
            self,
            "删除模板",
            f"确定删除模板「{name}」吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.templates.pop(name, None)
        self.template_combo.blockSignals(True)
        index = self.template_combo.findText(name)
        if index >= 0:
            self.template_combo.removeItem(index)
        self.template_combo.blockSignals(False)
        self._load_template(self.template_combo.currentText())

    def _save_current_template(self) -> None:
        name = self.current_template_name
        if name not in self.templates:
            return
        self.templates[name].update(
            {
                "labels": self._collect_labels(),
                "steps": self._collect_steps(),
                "rois": self.roi_canvas.get_rois(),
            }
        )
        self._save_template_to_flow_dir(name)
        self.set_tip(f"操作提示：模板「{name}」已保存当前配置。")

    def _roi_options(self) -> list[str]:
        options = ["全图"]
        for roi in self.roi_canvas.get_rois():
            name = roi.get("name")
            if name:
                options.append(name)
        return options

    def _open_roi_editor(self) -> None:
        dialog = RoiEditorDialog(self.roi_canvas.get_rois(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.roi_canvas.set_rois(dialog.selected_rois())
        if self.current_template_name in self.templates:
            self.templates[self.current_template_name]["rois"] = self.roi_canvas.get_rois()
        self.set_tip("操作提示：ROI 配置已更新，点击“保存当前”可写入 flow 目录。")

    def _save_template_to_flow_dir(self, template_name: str) -> None:
        """将模板保存到 flow/<模板名>/template.yaml。

        该目录名作为查询顶级索引，目录内保存模型、标签、ROI 和流程配置。
        """
        template = self.templates.get(template_name)
        if template is None:
            return
        self.config_service.save_template(
            template_name,
            {
                "name": template.get("name", template_name),
                "model_file": template.get("model_file", ""),
                "labels": template.get("labels", []),
                "rois": template.get("rois", []),
                "steps": template.get("steps", []),
            },
        )

    def auto_save_config(self) -> None:
        self._save_current_template()

    def _load_model(self) -> None:
        # 插入点：实际模型加载器（ONNX Runtime / OpenVINO / TensorRT）可在此替换。
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "加载模型",
            "",
            "模型文件 (*.pt *.pth *.onnx *.engine *.bin);;所有文件 (*.*)",
        )
        if not file_path:
            return
        self.templates[self.current_template_name]["model_file"] = file_path
        self.model_file_label.setText(f"模型文件：{file_path}")
        self.set_result(f"检测结果：模型已加载：{file_path}")

    def _load_labels(self) -> None:
        # 插入点：可从模型元数据或标注文件读取标签，替换下面的默认/文本读取逻辑。
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "加载标签",
            "",
            "标签文件 (*.txt *.names *.json);;所有文件 (*.*)",
        )
        if file_path:
            labels = []
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        name = line.strip()
                        if name:
                            labels.append(name)
            except OSError:
                labels = ["person", "helmet"]
            self.templates[self.current_template_name]["labels"] = labels
            self._populate_labels(labels)
        else:
            self._populate_labels(self.templates[self.current_template_name]["labels"])

    def _clear_labels(self) -> None:
        self.templates[self.current_template_name]["labels"] = []
        self.label_table.setRowCount(0)

    def _populate_labels(self, labels: list[str]) -> None:
        self.label_table.setRowCount(0)
        for english in labels:
            row = self.label_table.rowCount()
            self.label_table.insertRow(row)

            english_item = QTableWidgetItem(english)
            english_item.setFlags(english_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            english_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.label_table.setItem(row, 0, english_item)

    def _collect_labels(self) -> list[str]:
        labels = []
        for row in range(self.label_table.rowCount()):
            item = self.label_table.item(row, 0)
            english = item.text().strip() if item else ""
            if english:
                labels.append(english)
        return labels

    def _add_step(
        self,
        step_name: str = "新步骤",
        roi: str | None = None,
        label: str | None = None,
        confidence: float = 0.5,
        detection_count: int = 20,
        use_gesture: bool = False,
        gesture: str = "无",
        enabled: bool = True,
    ) -> None:
        row = self.flow_table.rowCount()
        self.flow_table.insertRow(row)

        step_item = QTableWidgetItem(step_name)
        step_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.flow_table.setItem(row, 0, step_item)

        roi_combo = QComboBox()
        roi_options = self._roi_options()
        roi_combo.addItems(roi_options)
        if roi in roi_options:
            roi_combo.setCurrentText(roi)
        self.flow_table.setCellWidget(row, 1, roi_combo)

        label_combo = QComboBox()
        labels = self._collect_labels()
        label_combo.addItems(labels or ["未定义标签"])
        if label in labels:
            label_combo.setCurrentText(label)
        self.flow_table.setCellWidget(row, 2, label_combo)

        confidence_spin = QDoubleSpinBox()
        confidence_spin.setRange(0.01, 1.0)
        confidence_spin.setSingleStep(0.05)
        confidence_spin.setValue(confidence)
        self.flow_table.setCellWidget(row, 3, confidence_spin)

        detection_count_spin = QSpinBox()
        detection_count_spin.setRange(1, 1000)
        detection_count_spin.setValue(detection_count)
        self.flow_table.setCellWidget(row, 4, detection_count_spin)

        use_gesture_check = QCheckBox()
        use_gesture_check.setChecked(use_gesture)
        self.flow_table.setCellWidget(row, 5, self._centered_checkbox(use_gesture_check))

        gesture_combo = QComboBox()
        gesture_combo.addItems(self.GESTURES)
        gesture_combo.setCurrentText(gesture)
        gesture_combo.setEnabled(use_gesture)
        use_gesture_check.toggled.connect(gesture_combo.setEnabled)
        self.flow_table.setCellWidget(row, 6, gesture_combo)

        enabled_check = QCheckBox()
        enabled_check.setChecked(enabled)
        self.flow_table.setCellWidget(row, 7, self._centered_checkbox(enabled_check))
        self.flow_table.setRowHeight(row, 36)

    @staticmethod
    def _centered_checkbox(checkbox: QCheckBox) -> QWidget:
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(checkbox)
        return widget

    def _collect_steps(self) -> list[dict]:
        steps = []
        for row in range(self.flow_table.rowCount()):
            name_item = self.flow_table.item(row, 0)
            roi_widget = self.flow_table.cellWidget(row, 1)
            label_widget = self.flow_table.cellWidget(row, 2)
            confidence_widget = self.flow_table.cellWidget(row, 3)
            detection_count_widget = self.flow_table.cellWidget(row, 4)
            use_gesture_widget = self.flow_table.cellWidget(row, 5)
            gesture_widget = self.flow_table.cellWidget(row, 6)
            enabled_widget = self.flow_table.cellWidget(row, 7)
            enabled = self._checkbox_value(enabled_widget, True)
            steps.append(
                {
                    "name": name_item.text() if name_item else "新步骤",
                    "roi": roi_widget.currentText() if isinstance(roi_widget, QComboBox) else "全图",
                    "label": label_widget.currentText() if isinstance(label_widget, QComboBox) else "",
                    "confidence": confidence_widget.value() if isinstance(confidence_widget, QDoubleSpinBox) else 0.5,
                    "detection_count": detection_count_widget.value() if isinstance(detection_count_widget, QSpinBox) else 20,
                    "use_gesture": self._checkbox_value(use_gesture_widget, False),
                    "gesture": gesture_widget.currentText() if isinstance(gesture_widget, QComboBox) else "无",
                    "enabled": enabled,
                }
            )
        return steps

    @staticmethod
    def _checkbox_value(widget: QWidget | None, default: bool) -> bool:
        if widget is None:
            return default
        checkbox = widget.findChild(QCheckBox)
        return checkbox.isChecked() if checkbox is not None else default

    def _execute_selected_step(self) -> None:
        row = self.flow_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "提示", "请先选中要执行的检测步骤。")
            return

        box = QMessageBox(self)
        box.setWindowTitle("单次执行")
        box.setText("请选择当前步骤的执行结果：")
        ok_button = box.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        ng_button = box.addButton("NG", QMessageBox.ButtonRole.RejectRole)
        box.exec()

        if box.clickedButton() is ok_button:
            self._set_row_color(row, "#3b7d5a")
            self.set_tip("操作提示：当前步骤单次执行结果为 OK，已标记为绿色。")
        elif box.clickedButton() is ng_button:
            self._set_row_color(row, "#a38a3b")
            self.set_tip("操作提示：当前步骤单次执行结果为 NG，已标记为黄色。")

    def _set_row_color(self, row: int, color: str) -> None:
        for column in range(self.flow_table.columnCount()):
            item = self.flow_table.item(row, column)
            if item is not None:
                item.setBackground(QColor(color))
            widget = self.flow_table.cellWidget(row, column)
            if widget is not None:
                widget.setStyleSheet(f"background-color: {color};")

    def _delete_selected_step(self) -> None:
        rows = sorted({index.row() for index in self.flow_table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.flow_table.removeRow(row)

    def _move_step(self, direction: int) -> None:
        row = self.flow_table.currentRow()
        target = row + direction
        if row < 0 or target < 0 or target >= self.flow_table.rowCount():
            return

        source = [self._take_row_value(row, col) for col in range(self.flow_table.columnCount())]
        target_data = [self._take_row_value(target, col) for col in range(self.flow_table.columnCount())]

        for column in range(self.flow_table.columnCount()):
            self._set_row_value(row, column, target_data[column])
            self._set_row_value(target, column, source[column])

        self.flow_table.setCurrentCell(target, 0)

    def _take_row_value(self, row: int, col: int):
        widget = self.flow_table.cellWidget(row, col)
        if isinstance(widget, QComboBox):
            return widget.currentText()
        if isinstance(widget, QDoubleSpinBox):
            return widget.value()
        if isinstance(widget, QSpinBox):
            return widget.value()
        if isinstance(widget, QWidget):
            checkbox = widget.findChild(QCheckBox)
            if checkbox is not None:
                return checkbox.isChecked()
        item = self.flow_table.item(row, col)
        return item.text() if item is not None else ""

    def _set_row_value(self, row: int, column: int, value) -> None:
        if column == 0:
            item = self.flow_table.item(row, column)
            if item is None:
                item = QTableWidgetItem()
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.flow_table.setItem(row, column, item)
            item.setText(str(value))
            return

        if column in (1, 2, 6):
            combo = self.flow_table.cellWidget(row, column)
            if isinstance(combo, QComboBox):
                combo.setCurrentText(str(value))
            return

        if column == 3:
            spin = self.flow_table.cellWidget(row, column)
            if isinstance(spin, QDoubleSpinBox):
                spin.setValue(float(value))
            return

        if column == 4:
            spin = self.flow_table.cellWidget(row, column)
            if isinstance(spin, QSpinBox):
                spin.setValue(int(value))
            return

        if column in (5, 7):
            checkbox_widget = self.flow_table.cellWidget(row, column)
            if checkbox_widget is not None:
                checkbox = checkbox_widget.findChild(QCheckBox)
                if checkbox is not None:
                    checkbox.setChecked(bool(value))

    def _toggle_label_panel(self) -> None:
        hidden = self.label_panel.isVisible()
        self.label_panel.setVisible(not hidden)
        self.toggle_label_button.setText("显示模板/标签栏" if hidden else "隐藏模板/标签栏")


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from app.standalone import run_page

    raise SystemExit(run_page(sys.modules[__name__].FlowPage))
