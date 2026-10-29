# NOTICE — 来源与归属

## 代码来源

本仓库三个脚本是**比赛现场运行的版本**，由作者（3 人队成员之一）提交，未经功能性改写。为便于阅读仅做了路径整理（`pharmacy_pkg/scripts/` 保持原 ROS 包结构）。

| 本仓库文件 | 基础 | 相似度（difflib, 行级） | 说明 |
| --- | --- | --- | --- |
| `src/pharmacy_pkg/scripts/F1_yaofang.py` | 厂商包 `pharmacy_pkg/scripts/F1_yaofang.py`（476 行） | **0.07** | 结构上沿用厂商 demo 的 `waypoints`/四元数写法，逻辑主体重写：新增裁判上报、识别结果校验与回退、语音播报、分阶段任务码 |
| `src/pharmacy_pkg/scripts/F1_detect_code.py` | 厂商包 `pharmacy_pkg/scripts/F1_detect_code.py`（408 行） | **0.82** | 在厂商识别脚本上改造：定位框门限放宽（48 → 40–56）、透视归一化后四区域切片、`/request_recognition` 服务化、缓存重发 |
| `src/pharmacy_pkg/scripts/OCR_CAM.py` | 厂商包 `pharmacy_pkg/scripts/OCR_CAM_0506.py`（78 行） | **0.08** | 重写为 ROS 节点：ROI + 自适应阈值 + Tesseract PSM 6 + 关键词/秒数解析 + 10 Hz 发布 + 统计 |

相似度用 `difflib.SequenceMatcher(None, a.splitlines(), b.splitlines()).ratio()` 计算，比较对象是厂商资料包 `D:\F1` 中的原始脚本（仓库内不包含该资料包）。

## 平台与第三方

- **EPRobot V2.0** 教学平台、底盘固件（STM32F407VET6）、`base_control`/`robot_navigation`/`astra_camera` 等 launch 与驱动：厂商提供，不在本仓库内
- **RPLIDAR A1（A1M8）** 驱动 `rplidar_ros`：厂商/SLAMTEC 提供
- **move_base / amcl / teb_local_planner**：ROS 社区包
- **pyzbar / zbar**、**Tesseract + chi_sim**、**web_video_server**：各自许可证（zbar LGPL-2.1、Tesseract Apache-2.0、web_video_server BSD）

## 硬件参数

| 项 | 值 | 出处 |
| --- | --- | --- |
| 车型 | EPRobot V2.0 | 厂商资料 `EPV2.0-ROS智能车资料链接.docx`、平台手册 |
| 底盘 MCU | STM32F407VET6 | 用户提供（原文写作 `STM32F407VET62`，按 ST 料号规则归一化，**待与实物丝印核对**） |
| 激光雷达 | SLAMTEC RPLIDAR A1，手册标注 A1M8 | 用户提供 + 厂商手册 |
| 深度相机 | Orbbec Astra | 厂商 demo 启动方式 `roslaunch astra_camera astra.launch`（`竞赛程序说明.docx`） |
| 底盘串口 | `/dev/ttyUSB0` @ 115200 | 厂商 `base_control.launch` |

## 未包含的内容

- 厂商资料包（手册、PDF、镜像、视频、裁判软件 exe）
- 赛场地图（`.pgm`/`.yaml`）与预录语音 `*.mp3`：体积大且与场地绑定，仓库只保留引用路径
- 队友编写的部分（本仓库 3 个节点为作者实现；建图、部分导航参数调优为队内协作）

## 关于 `docs/` 中的自评

`docs/06-缺陷清单.md` 与 `RESUME.md` 的「已知问题」是**赛后复盘**，不是比赛当时的改动记录。判断依据是代码本身（行号可查），不涉及任何对队友工作的评价。
