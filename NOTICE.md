# NOTICE — 来源与归属

## 代码来源

本仓库三个脚本是**比赛现场运行的版本**，由作者（3 人队成员之一）提交，未经功能性改写。为便于阅读仅做了路径整理（`pharmacy_pkg/scripts/` 保持原 ROS 包结构）。

| 本仓库文件 | 基础 | 相似度（difflib, 行级） | 说明 |
| --- | --- | --- | --- |
| `src/pharmacy_pkg/scripts/F1_yaofang.py` | 厂商包 `pharmacy_pkg/scripts/F1_yaofang.py`（476 行） | **0.07** | 结构上沿用厂商 demo 的 `waypoints`/四元数写法，逻辑主体重写：新增裁判上报、识别结果校验与回退、语音播报、分阶段任务码 |
| `src/pharmacy_pkg/scripts/F1_detect_code.py` | 厂商包 `pharmacy_pkg/scripts/F1_detect_code.py`（408 行） | **0.82** | 在厂商识别脚本上改造：定位框门限放宽（48 → 40–56）、透视归一化后四区域切片、`/request_recognition` 服务化、缓存重发 |
| `src/pharmacy_pkg/scripts/OCR_CAM.py` | 厂商包 `pharmacy_pkg/scripts/OCR_CAM_0506.py`（78 行） | **0.08** | 重写为 ROS 节点：ROI + 自适应阈值 + Tesseract PSM 6 + 关键词/秒数解析 + 10 Hz 发布 + 统计 |

相似度用 `difflib.SequenceMatcher(None, a.splitlines(), b.splitlines()).ratio()` 计算，比较对象是厂商资料包 `D:\F1` 中的原始脚本（仓库内不包含该资料包）。

## `vendor/multi_robot_joy/` —— 厂商课程包，**非本人实现**

`vendor/multi_robot_joy/` 是厂商/助教发放的**多机协同课程包**（`D:\F1\小车课程资料\多机协同配置与操作`），原样收录，作者未改动一行：

| 文件 | 来源 | 归属 |
| --- | --- | --- |
| `vendor/multi_robot_joy/eprobot_joy/**` | 课程包内 `eprobot_joy/` 包 | 厂商（`package.xml` 的 `maintainer` 为 `ubuntu@todo.todo`，`<license>TODO</license>` 未填，**实际许可不明**） |
| `vendor/multi_robot_joy/EPRobot_joy_{master,slave}.launch` | 课程包内同名文件 | 厂商 |
| `vendor/multi_robot_joy/参考配置文件/{hosts,hostname}` | 课程包内 `参考配置文件/` | 厂商（`.bashrc` 未收录，避免夹带整份发行版配置） |

**收录目的仅为止于留档与面试对照**：作者读过这套实现，并在 `docs/09-多机协同（ROS 主从）.md` 与 `vendor/multi_robot_joy/README.md` 中逐项梳理机制与行号。它解决的是「多台车能被同一个 master 看见、能被一只手柄同时驱动」，**不含任何任务分配、结果交换或避让逻辑**——那部分本仓库没有留存（见 `docs/08`）。

## 平台与第三方

- **EPRobot V2.0** 教学平台、底盘固件（STM32F407VET6）、`base_control`/`robot_navigation`/`astra_camera` 等 launch 与驱动：厂商提供，不在本仓库内
- **RPLIDAR A1（A1M8）** 驱动 `rplidar_ros`：厂商/SLAMTEC 提供
- **move_base / amcl / teb_local_planner**：ROS 社区包
- **pyzbar / zbar**、**Tesseract + chi_sim**、**web_video_server**：各自许可证（zbar LGPL-2.1、Tesseract Apache-2.0、web_video_server BSD）

## 硬件参数

| 项 | 值 | 出处 |
| --- | --- | --- |
| 车型 | EPRobot V2.0 | 厂商资料 `EPV2.0-ROS智能车资料链接.docx`、平台手册 |
| 底盘 MCU | STM32F407VET6 | 作者提供（最初写作 `STM32F407VET62`，已确认是笔误；料号规则也指向 VET6：LQFP100 / 512 KB Flash / 带以太网 MAC） |
| 激光雷达 | SLAMTEC RPLIDAR A1，手册标注 A1M8 | 用户提供 + 厂商手册 |
| 深度相机 | Orbbec Astra | 厂商 demo 启动方式 `roslaunch astra_camera astra.launch`（`竞赛程序说明.docx`） |
| 底盘串口 | `/dev/ttyUSB0` @ 115200 | 厂商 `base_control.launch` |

## 未包含的内容

- 厂商资料包（手册、PDF、镜像、视频、裁判软件 exe）
- 赛场地图（`.pgm`/`.yaml`）与预录语音 `*.mp3`：体积大且与场地绑定，仓库只保留引用路径
- 队友编写的部分（本仓库 3 个节点为作者实现；建图、部分导航参数调优为队内协作）

## 关于 `docs/` 中的自评

`docs/06-缺陷清单.md` 与 `RESUME.md` 的「已知问题」是**赛后复盘**，不是比赛当时的改动记录。判断依据是代码本身（行号可查），不涉及任何对队友工作的评价。
