# 09 多机协同：这一包资料里有什么、缺什么

`D:\F1\小车课程资料\多机协同配置与操作` 是厂商/助教发的**多机协同课程包**。结论先说：**有「多机跑起来」的完整基础设施，没有「多机协同」的决策代码**。

> 源码已收录到仓库 [`vendor/multi_robot_joy/`](../vendor/multi_robot_joy/README.md)（**厂商代码，非本人实现**，归属见 `NOTICE.md`）。下文提到的路径以仓库内 `vendor/multi_robot_joy/...` 为准，点开可对照行号。

## 包里的东西

| 条目 | 类型 | 内容 |
| --- | --- | --- |
| `eprobot_joy/`（仓库内 `vendor/multi_robot_joy/eprobot_joy/`） | **可编译源码** | 一个 ROS 节点：从 `/dev/input/js0` 读 PS2 手柄，**同时向 3 个话题发同一份 `Twist`**，带按键位掩码逐个开关 |
| `EPRobot_joy_master.launch` / `_slave.launch`（仓库内同路径） | 启动文件 | 主机拉起底盘节点 + 手柄节点；从机只拉底盘节点（手柄节点整段被注释） |
| `参考配置文件/{hostname, hosts, .bashrc}`（仓库收前两个，`.bashrc` 仅摘三条 `export`） | 配置样例 | 一台车的网络名与主从环境变量样例 |
| `EPRobot多机通讯的配置方法.pdf` | 文档 | 原理 + 局域网配置 + 主从机配置（含 AP→client 模式改造、`wpa_supplicant`） |
| `多机协同操作说明.docx` | 文档 | 手柄增补功能、主从启动顺序、如何改成程序控制 |
| `相关底层代码/` | 厂商底层 | `eprobot_start`（含 `art_racecar.py` 底盘驱动、`F1_demo.py`）、`robot_navigation`（地图/参数/launch/`show_mark.py`）、`navigation-melodic`（整份 ROS 导航栈源码） |

## 多机协同是怎么做的（机制，不是我写的，但操作会）

**1. 一主多从的 ROS 网络**：全部树莓派从 AP 模式改成 client 模式接同一路由器，路由器做 MAC-IP 绑定保证地址固定；`hostname` 写本机网络名，`hosts` 把网络名与 `127.0.1.1` 绑定并写上彼此的地址，`.bashrc` 里指定 master：

```bash
export ROS_MASTER_URI=http://EPRobot1:11311
export ROS_IP=EPRobot1
```

**2. 命名空间隔离**：每台车用 `robot_name` 参数区分，底盘节点把 `cmd_vel` remap 到 `$(arg robot_name)/cmd_vel`，于是同一 master 下每台车各有一个 `EPRobotN/cmd_vel`，互不串车。

**3. 遥控扇出**：手柄节点一次 advertise 三个 publisher，把同一份速度指令打到 `EPRobot1/2/3/cmd_vel`：

```cpp
nh_private.param<std::string>("pub_topic",  pub_topic,  "cmd_vel");
nh_private.param<std::string>("pub_topic1", pub_topic1, "cmd_vel1");
nh_private.param<std::string>("pub_topic2", pub_topic2, "cmd_vel2");
cmd_vel_pub  = n.advertise<geometry_msgs::Twist>(pub_topic,  1000);
```

用位掩码控制「这一帧发给谁」——`EN_1=0x01`、`EN_2=0x02`、`EN_3=0x04`、`EN_ALL=0x07`，20 Hz 循环里按 `pub_en & EN_n` 逐路 `publish`。手柄 `MODE` 红灯亮起后（`JS_MODE_2`）：`Y` 全开/全关，`B` 第一路，`A` 第二路，`X` 第三路。

**4. 程序控制多车**：说明文档明确写「把两个 launch 的第 30–39 行（手柄节点）注释掉，自己发布 `EPRobot1/cmd_vel`、`EPRobot2/cmd_vel`、`EPRobot3/cmd_vel` 即可」——也就是**协同控制的手柄部分是可替换的，接口就是三路话题**。

## 缺的是什么

这一包解决的是「多台车能被同一个 master 看见、能被同一个手柄按需驱动」。它**没有**：

- 任务分配（谁去 A 窗口、谁去 B 窗口）
- 车与车之间的状态/结果交换（`eprobot_joy` 只发 `cmd_vel`，从不订阅任何东西）
- 冲突避让、排队、死锁处理
- 任何自主决策节点——`multi_points_navigation.launch` 只是`robot_pose_publisher` + `show_mark.py`（把多点导航的可视化标记画出来），不涉及多车协调

所以「多机协同的代码」在这一包里 = **基础设施 + 遥控扇出**；真正的协同策略要自己写。

## 与比赛版的关系（为什么比赛没走 ROS 主从）

比赛现场的网络由主办方发放，改 `hostname`/`hosts`/`.bashrc` 会牵动整台车的环境；而赛事要求的是「每台车把自己的状态报给裁判软件」，只依赖一个 IP + 一个端口。所以比赛版选择了**单车闭环 + TCP 上报裁判**：上层协调责任交给裁判端，车侧只保证「上报稳定、断线重连」。

这也解释了早期双车版本为什么用 TCP 直连而不是 ROS 主从：要传的是**识别结果**（一串整数），不是速度指令；走 socket 一跳就到，不必把两车的 ROS 图并成一个 master。

## 这份资料里值得留意的两处

1. **配置样例与文档自相矛盾**：PDF 明确「两车以上的多机协同只能够使用 `ROS_IP`」，但 `参考配置文件/.bashrc` 里写的是 `export ROS_IP=EPRobot1`（主机名，不是 IP 地址）。两台车时靠 `hosts` 解析能蒙对，三台车以上容易出现「master 看见了节点、话题却收不到」这类难查的问题。**照抄样例前先按文档改**。
2. **课程资料里带明文默认密码**（`sudo` 与 `wpa_supplicant` 相关）。本仓库不收录任何密码；真要按这份资料配置，密码属于厂商默认值，上公网前必须改。

## 如果要真的做多机协同

按这一包给的基础设施，缺的那层最小实现是：一个「任务分配节点」订阅各车的 `/EPRobotN/odom` 与识别结果，发布各车的 `EPRobotN/move_base_simple/goal`；再加一层「窗口占用表」避免两车同时去同一个体检窗口。**难点不在通信，在「谁在什么时候去哪里」的时序约束**——这与比赛版把协调交给裁判端是同一问题的两种解法。
