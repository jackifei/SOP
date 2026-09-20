# CAM Hand：USB 相机手势识别

一个用 Python + OpenCV 编写的实时手势识别应用，支持 USB 摄像头。

## 功能

- 实时摄像头预览，默认自动选择第一个可用摄像头
- 手势识别：拳头（Fist）、张开手掌（Open Palm）、竖大拇指（Thumbs Up）、比 V（Peace）、食指指向（Pointing）、OK 手势、ILY 手势
- 自动选择识别后端：已安装 MediaPipe 时使用 21 个手部关键点；未安装时回退到 OpenCV 肤色分割 + 凸包凹陷点方案
- 快捷键切换摄像头、镜像、截图、开关检测
- `--snapshot` 模式：采集一帧并输出检测结果，方便测试和无界面环境使用

## 安装

建议使用 Python 3.10+。

```powershell
cd H:\codexpj\cam_hand
python -m pip install -r requirements.txt
```

推荐额外安装 MediaPipe，识别准确度会明显更高：

```powershell
python -m pip install mediapipe
```

未安装 MediaPipe 也可以运行，应用会自动使用 OpenCV 后端。

MediaPipe 1.0 使用 Tasks API，需要项目内的 models/hand_landmarker.task 模型文件（本仓库已附带）。

## 运行

```powershell
python run.py
```

指定摄像头、分辨率或识别后端：

```powershell
python run.py --camera 1 --width 1280 --height 720
python run.py --backend mediapipe
python run.py --list-cameras
```

## 快捷键

| 按键 | 功能 |
| --- | --- |
| `Q` / `Esc` | 退出 |
| `H` | 显示/隐藏帮助 |
| `D` | 开关手势检测 |
| `R` | 开关镜像预览 |
| `S` | 保存当前帧截图到 `screenshots/` |
| `0`-`9` | 切换到对应编号的摄像头 |

## 单帧测试

不需要打开窗口，也可以采集一帧并保存带标注的图片：

```powershell
python run.py --snapshot result.png
```

## 项目结构

```text
cam_hand/
  camera.py     # USB 摄像头封装与枚举
  detector.py   # MediaPipe / OpenCV 双后端检测器
  gestures.py   # 手势分类逻辑
  ui.py         # OpenCV 实时窗口与绘制
  app.py        # 命令行入口
models/         # MediaPipe 手部关键点模型文件
tests/          # 手势分类单元测试
```

## 常见问题

- 提示找不到摄像头：先运行 `python run.py --list-cameras` 查看可用编号，再用 `--camera N` 指定。
- 画面方向相反：默认镜像预览；需要原始方向时使用 `python run.py --no-mirror`。
- 纯 OpenCV 后端对光线比较敏感：尽量在均匀、明亮的背景前使用，或安装 MediaPipe 提高稳定性。

