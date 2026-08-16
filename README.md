# SOP 框架 Demo

基于 Python 3.12 和 PyQt6 的桌面应用框架 demo，用于相机管理、检测流程编辑、硬件配置、结果查询、MES 对接等工业视觉软件场景。

## 运行环境

- Python 3.12
- PyQt6 >= 6.6

安装依赖：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

启动程序：

```powershell
python main.py
```

## PyInstaller 打包

安装打包工具：

```powershell
python -m pip install pyinstaller
```

打包 `main.py` 为单个 exe，并同时打包 `config`、`flow` 目录：

```powershell
pyinstaller --noconfirm --windowed --onefile --name SOP --add-data "config;config" --add-data "flow;flow" main.py
```
打包小exe，附加配置文件，运行时自动创建
```
pyinstaller -D main.py --noconfirm --windowed --icon=MyAppLog.ico --name SOP_APP --uac-admin --add-data "config;config" --add-data "flow;flow"
```
说明：Windows 下 `--add-data` 使用分号 `;` 分隔源目录和目标目录；Linux/macOS 使用冒号 `:`。

## 已实现内容

- 顶部水平导航栏，包含 9 个功能页面和帮助按钮
- 底部 VSCode 风格状态栏，可动态设置状态项
- 页面顶部不再显示页面名称，改为显示检测结果和操作提示
- 相机管理页：左侧图像显示区、右侧参数设置区和 ROI 设置区，中间支持鼠标拖动调整宽度
- 运行看板页：左侧相机画面与 ROI 显示，右侧流程步骤状态，展示当前模板、OK/NG、日/周/月统计和 OK 完成率
- 流程编辑页：产品模板管理、模型加载、英文/中文标签映射、检测流程配置、置信度/检测数量/手势设置，标签栏可隐藏
- 硬件配置页：串口打开/关闭、固定串口参数，以及 ModbusTCP 的 16 路输入指示灯和 16 路输出开关
- 结果查询页：按时间范围、产品、完成状态和报警状态筛选检测记录
- MES 对接页：勾选上报报文类型，预留自定义报文模板
- 日志页：级别筛选、测试日志、清空和导出占位
- 参数页：相机、检测、系统参数分组
- 人员管理页：人员列表及增删改查占位
- 每个页面都可以作为独立窗口单独运行，便于调试
- `ui/` 目录提供基础 `.ui` 文件，`oriui/` 目录提供更接近当前暗黑显示效果的 `.ui` 文件

## 项目结构

```text
SOP/
├─ main.py
├─ requirements.txt
├─ PROJECT_ARCHITECTURE.md
├─ config/
│  └─ README.md
├─ flow/
│  └─ README.md
├─ drivers/
│  ├─ camera/
│  ├─ io/
│  └─ mes/
├─ algorithms/
├─ ui/
│  ├─ camera_page.ui
│  ├─ run_dashboard_page.ui
│  ├─ flow_page.ui
│  ├─ hardware_config_page.ui
│  ├─ result_query_page.ui
│  ├─ mes_page.ui
│  ├─ log_page.ui
│  ├─ parameters_page.ui
│  ├─ personnel_page.ui
│  └─ main_window.ui
├─ oriui/
│  ├─ camera_page.ui
│  ├─ run_dashboard_page.ui
│  ├─ flow_page.ui
│  ├─ hardware_config_page.ui
│  ├─ result_query_page.ui
│  ├─ mes_page.ui
│  ├─ log_page.ui
│  ├─ parameters_page.ui
│  ├─ personnel_page.ui
│  └─ main_window.ui
└─ app/
   ├─ main_window.py
   ├─ status_bar.py
   ├─ help_dialog.py
   ├─ standalone.py
   ├─ theme.py
   ├─ services/
   │  ├─ __init__.py
   │  ├─ config_service.py
   │  └─ dashboard_service.py
   ├─ widgets/
   │  ├─ __init__.py
   │  ├─ camera_view.py
   │  ├─ roi_canvas.py
   │  ├─ roi_editor.py
   │  └─ stat_card.py
   └─ pages/
      ├─ base_page.py
      ├─ camera_page.py
      ├─ run_dashboard_page.py
      ├─ flow_page.py
      ├─ hardware_config_page.py
      ├─ result_query_page.py
      ├─ mes_page.py
      ├─ log_page.py
      ├─ parameters_page.py
      └─ personnel_page.py
```

## 扩展说明

- 新增页面时，在 `app/pages/` 下创建页面类，继承 `BasePage`，然后将其加入 `app/main_window.py` 的 `NAV_ITEMS`。
- 底部状态栏通过 `MainWindow.status_bar.set_status(key, text, kind)` 更新，`kind` 支持 `info`、`ok`、`warn`、`error`。
- 页面配置由 `app/services/config_service.py` 保存为 `config/<页面名>.yaml`。
- 流程模板由 `flow/<模板名>/template.yaml` 保存，模板名目录作为查询顶级索引。
- 独立调试页面示例：`python app/pages/camera_page.py`
- 运行看板独立调试：`python app/pages/run_dashboard_page.py`
- Qt Designer 二次编辑：打开 `ui/*.ui` 或 `oriui/*.ui`，修改后可用 `pyuic6` 生成 Python UI 代码。
- 当前为 UI/交互框架 demo，相机采集、ModbusTCP、MES、数据库和流程引擎等业务逻辑尚未接入，可在代码中标记的“插入点”继续实现。
