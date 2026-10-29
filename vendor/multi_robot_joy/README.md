# vendor/multi_robot_joy —— 厂商课程包（**非本人实现**）

本目录原样收录自厂商/助教随车资料 `D:\F1\小车课程资料\多机协同配置与操作`，用于留档与面试讲解时对照。**代码作者不是本文档作者**，请勿把它算作参赛者的实现成果。

收录理由：这套代码是「一台手柄同时控三台车」的完整可编译实现，也是理解 ROS 一主多从 + 命名空间隔离的最小样例。作者读过并在 `docs/09-多机协同（ROS 主从）.md` 中逐项梳理，因此保留源码以便对照行号。

## 文件清单

| 文件 | 行数 | 说明 |
| --- | --- | --- |
| `eprobot_joy/src/eprobot_joy.cpp` | 157 | 手柄读取 + 三路 `Twist` 扇出 |
| `eprobot_joy/include/eprobot_joy/eprobot_joy.h` | 63 | 话题名、使能位掩码、手柄模式宏 |
| `eprobot_joy/CMakeLists.txt` | — | catkin 构建（`roscpp`、`geometry_msgs`、`nav_msgs`、`tf`、`roslib`） |
| `eprobot_joy/package.xml` | — | `maintainer email="ubuntu@todo.todo"`、`<license>TODO</license>`（见文末「许可」） |
| `eprobot_joy/launch/eprobot_ps2_control.launch` | — | 单机调试用：`/dev/input/js0`、`maxLinear_x=0.5`、`maxAngular_z=2.5`、`joystick_mode=2` |
| `EPRobot_joy_master.launch` | 42 | 主机：底盘 `art_racecar.py` + 手柄节点 + 三路 `pub_topic*` |
| `EPRobot_joy_slave.launch` | 42 | 从机：仅底盘节点，手柄节点整段注释 |
| `参考配置文件/hosts`、`hostname` | — | 网络名与地址样例（`.bashrc` 未收录，两条关键 `export` 见下） |

`.bashrc` 没有整份复制（避免把一份 130 行的发行版默认 bashrc 塞进仓库）。与原样例相关的只有末尾三行：

```bash
source /opt/ros/melodic/setup.bash
export ROS_MASTER_URI=http://EPRobot1:11311
export ROS_IP=EPRobot1
```

## 源码导读（按行号）

- `eprobot_joy.cpp:10` — `pub_en = EN_ALL;` 初始全部使能
- `eprobot_joy.cpp:25-27` — 三个 publisher，话题名来自 `pub_topic` / `pub_topic1` / `pub_topic2` 参数
- `eprobot_joy.cpp:44` — `ros::Rate rosSleep(20);` 20 Hz 主循环
- `eprobot_joy.cpp:96-118` — `JS_MODE_2` 下的按键：`case 0` 全开/全关（`:97-100`）、`case 1/2/3` 对应 `EN_1/EN_2/EN_3` 的位取反与置位（`:102-118`）
- `eprobot_joy.cpp:130` — 线速度死区：`|linear.x| < 0.09` 归零，抑制摇杆零漂
- `eprobot_joy.cpp:137-142` — 发布门控：`if(pub_en & EN_N) cmd_vel_pubN.publish(vel_msg_)`
- `eprobot_joy.h:29-33` — `EN_1=0x01`、`EN_2=0x02`、`EN_3=0x04`、`EN_ALL=0x07`、`DIS_ALL=0x00`

要点：**同一份 `Twist` 发往三个话题，没有反馈、没有分配、没有避让**。协同策略（谁去哪、谁先走）不在这套代码里——这正是 `docs/09` 指出的缺口。

## 命名空间与主从

`EPRobot_joy_master.launch:4,6,18` 把底盘节点名设为 `$(arg robot_name)`（默认 `EPRobot1`），并把它的 `cmd_vel` remap 到 `$(arg robot_name)/cmd_vel`；`:36-38` 让手柄的三路话题分别指向 `$(arg robot_group)1/2/3/cmd_vel`。于是同一个 master 下每台车只有一个命名空间内的 `cmd_vel`，互不串台。

## 未验证项

- **未在本机编译**：仓库环境没有 ROS/catkin（Python 侧也没有 `rospy`），本目录仅完成源码留档与静态阅读，未执行 `catkin_make`。
- **未实机运行**：三车联调需要三台树莓派同一局域网 + MAC-IP 绑定，作者本轮未复现。
- 若要在 Ubuntu 18.04 + ROS Melodic 上编译，按厂商说明放回 `catkin_ws/src/` 后 `catkin_make` 即可；`CMakeLists.txt` 是 `cmake_minimum_required(VERSION 2.8.3)` 的老式写法，新版 CMake 会告警。

## 两个坑（作者踩过的阅读理解层面问题）

1. **`ROS_IP=EPRobot1` 是主机名不是 IP**。厂商 PDF 写「两车以上只能用 `ROS_IP`」，但样例 `.bashrc` 给的却是主机名。两车靠 `hosts` 解析能蒙对，三车以上容易出现「master 上 `rosnode list` 看得见、话题互相收不到」。
2. 课程资料里带**明文默认密码**（AP 改造与 `sudo` 相关），本仓库一个字都没收录。上公网或换场地前必须改密码。

## 许可

`package.xml` 里 `<license>TODO</license>` 是 catkin 模板未填的默认值，**实际许可不明**。本目录仅作课程资料留档，不主张任何权利；如需再分发请联系平台方。
