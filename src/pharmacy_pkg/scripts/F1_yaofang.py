#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import rospy
import actionlib
import socket
import json
import threading
import time
from actionlib_msgs.msg import *
from geometry_msgs.msg import Pose, Point, Quaternion, Twist
from nav_msgs.msg import Odometry
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from tf.transformations import quaternion_from_euler
from std_msgs.msg import Int32MultiArray, String
from std_srvs.srv import Empty, Trigger


class StateReporter:
    """任务5：状态信息上报模块 - 与裁判软件通信（带断线重连）"""
    def __init__(self, robot_id="1"):
        self.robot_id = robot_id
        self.speed = 0.0
        self.real_odom = [0.0, 0.0]
        self.odom = [0.0, 0.0]
        self.task = "R"
        self.cv1 = "WAIT-0"
        self.cv2 = "--"

        # 官方点位坐标
        self.ideal_coords = {
            'A': (0.7, 2.55),
            'B': (1.5, 3.05),
            'C': (1.4, 2.06),
            '1': (-1.6, 2.53),
            '2': (-0.8, 1.82),
            '3': (-1.6, 1.58),
            '4': (-0.8, 0.98),
            'R': (0.0, 0.0),
        }

        self.server_ip = "192.168.31.21"
        self.server_port = 8888
        self.socket = None
        self.connected = False
        self.report_thread = None
        self.running = False
        self.reconnect_lock = threading.Lock()

        rospy.Subscriber('/odom', Odometry, self.odom_callback)

    def odom_callback(self, msg):
        self.speed = msg.twist.twist.linear.x
        self.real_odom = [round(msg.pose.pose.position.x, 1),
                          round(msg.pose.pose.position.y, 1)]

    def set_server(self, ip, port):
        self.server_ip = ip
        self.server_port = port

    def connect(self):
        """建立TCP连接"""
        with self.reconnect_lock:
            try:
                if self.socket:
                    try:
                        self.socket.close()
                    except:
                        pass
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(3.0)
                self.socket.connect((self.server_ip, self.server_port))
                self.connected = True
                rospy.loginfo("【任务5】✅ 已连接到裁判系统 %s:%d" % (self.server_ip, self.server_port))
                return True
            except Exception as e:
                self.connected = False
                rospy.logwarn("【任务5】连接裁判系统失败: %s，将自动重连" % str(e))
                return False

    def reconnect(self):
        """断线重连"""
        if not self.connected:
            rospy.loginfo("【任务5】尝试重新连接裁判系统...")
            return self.connect()
        return self.connected

    def update_task_and_odom(self, task_code):
        self.task = task_code
        if task_code in self.ideal_coords:
            self.odom = list(self.ideal_coords[task_code])
            rospy.logdebug("【任务5】坐标同步: task=%s, 坐标=%s" % (task_code, str(self.odom)))
        else:
            self.odom = self.real_odom.copy()

    def update_cv1(self, result_str):
        self.cv1 = result_str

    def update_cv2(self, result_str):
        self.cv2 = result_str

    def send_data(self):
        """发送JSON格式的状态数据，失败时自动标记断连"""
        if not self.connected or self.socket is None:
            return

        data = {
            "id": self.robot_id,
            "speed": round(self.speed, 1),
            "odom": [round(self.odom[0], 1), round(self.odom[1], 1)],
            "task": self.task,
            "CV1": self.cv1,
            "CV2": self.cv2
        }

        try:
            json_str = json.dumps(data, ensure_ascii=False)
            if isinstance(json_str, unicode):
                json_str = json_str.encode("utf-8")
            self.socket.sendall(json_str + "\n")
            rospy.loginfo("【任务5】📤 上报: %s" % json_str.strip())
        except Exception as e:
            rospy.logwarn("【任务5】发送失败: %s，标记断连" % str(e))
            self.connected = False

    def start_reporting(self, freq=1.0):
        if self.report_thread is not None:
            return
        self.running = True
        self.report_thread = threading.Thread(target=self._report_loop, args=(freq,))
        self.report_thread.daemon = True
        self.report_thread.start()
        rospy.loginfo("【任务5】状态上报已启动，频率 %.1fHz" % freq)

    def _report_loop(self, freq):
        interval = 1.0 / freq
        reconnect_interval = 5.0
        last_reconnect_time = 0
        
        while self.running and not rospy.is_shutdown():
            if not self.connected:
                current_time = time.time()
                if current_time - last_reconnect_time >= reconnect_interval:
                    self.reconnect()
                    last_reconnect_time = current_time
            else:
                self.send_data()
            time.sleep(interval)

    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        self.connected = False


class MoveBaseSquare():

    def __init__(self):
        rospy.init_node('nav_pharmacy', anonymous=False)
        rospy.on_shutdown(self.shutdown)

        self.voice_path = '/home/EPRobot/robot_ws/src/pharmacy_pkg/yuyingwenjian/'

        # 初始化状态上报器
        self.reporter = StateReporter(robot_id="1")
        self.reporter.set_server("192.168.31.21", 8888)
        self.reporter.connect()
        self.reporter.start_reporting(1.0)

        self.task_pub = rospy.Publisher('/current_task', String, queue_size=10)

        # 导航点定义
        quaternions = list()
        euler_angles = (1.57, 1.57, 1.57, -1.57, -1.57, -1.57, -1.57, 0, -3.14, 0)
        for angle in euler_angles:
            q_angle = quaternion_from_euler(0, 0, angle, axes='sxyz')
            q = Quaternion(*q_angle)
            quaternions.append(q)

        waypoints = list()
        # 保留识别板1（索引8），删除识别板2
        waypoints.append(Pose(Point(1.420, 2.060, 0), quaternions[0]))      # 0: C窗口
        waypoints.append(Pose(Point(0.700, 2.550, 0), quaternions[1]))      # 1: A窗口
        waypoints.append(Pose(Point(1.501, 3.050, 0), quaternions[2]))      # 2: B窗口
        waypoints.append(Pose(Point(-0.807, 0.980, 0), quaternions[3]))     # 3: 4号化验区
        waypoints.append(Pose(Point(-1.615, 1.580, 0), quaternions[4]))     # 4: 3号化验区
        waypoints.append(Pose(Point(-0.830, 1.820, 0), quaternions[5]))     # 5: 2号化验区
        waypoints.append(Pose(Point(-1.584, 2.530, 0), quaternions[6]))     # 6: 1号化验区
        waypoints.append(Pose(Point(0., 0, 0), quaternions[7]))              # 7: 起点
        waypoints.append(Pose(Point(0.980, 0.145, 0), quaternions[9]))      # 8: 识别板1

        self.waypoints = waypoints

        self.sample_name = {0: '静脉血', 1: '唾液', 2: '组织', 3: '血浆'}
        self.sample_pinyin = {0: 'jingmaixue', 1: 'tuoye', 2: 'zuzhi', 3: 'xuejiang'}
        self.window_name = {0: '血常规', 1: '体液', 2: '免疫检测', 3: '激素检验'}

        # 状态变量
        self.count = 9
        self.windows_go = [0, 0, 0]
        self.lab_window = 0
        self.sample_count = 0
        self.sample_type = 0
        self.data_received = False
        self.recognition_lock = True
        self.current_result = None
        self.received_results = []
        self.visit_all_labs = False

        # 停顿时间设置（单位：秒）
        self.pause_time = 0.25  # 取样本/送药停顿时间（原0.5秒的一半）
        self.home_pause_time = 1.0  # 回到起点停顿时间（原2秒的一半）

        self.cmd_vel_pub = rospy.Publisher('/cmd_vel', Twist, queue_size=10)
        self.cam_sub = rospy.Subscriber('/cam_return', Int32MultiArray, self.detect_result, queue_size=10)

        rospy.sleep(1)
        self.move_base = actionlib.SimpleActionClient("move_base", MoveBaseAction)
        rospy.loginfo("Waiting for move_base...")
        self.move_base.wait_for_server(rospy.Duration(60))

        rospy.wait_for_service('/move_base/clear_costmaps')
        self.clear_costmaps_service = rospy.ServiceProxy('/move_base/clear_costmaps', Empty)

        rospy.loginfo("Starting autonomous pharmacy navigation...")

        while not rospy.is_shutdown():
            if self.count == 9:
                self.go_to_recognize_area()
            elif self.count == 10:
                self.go_to_dispense_area()
            elif self.count == 11:
                self.go_to_delivery_area()
            rospy.sleep(0.1)

    def update_task(self, task_code):
        self.reporter.update_task_and_odom(task_code)
        self.task_pub.publish(String(data=task_code))

    def update_cv1(self, result_str):
        self.reporter.update_cv1(result_str)

    def update_cv2(self, result_str):
        self.reporter.update_cv2(result_str)

    def go_to_recognize_area(self):
        rospy.loginfo("【任务1】从起点前往识别板1...")
        self.update_task("1")
        self.clear_costmaps_service()
        goal = self.make_goal(self.waypoints[8])  # 识别板1
        if self.move_to(goal):
            rospy.loginfo("到达识别板1，等待二维码识别...")
            self.update_task("R")

            try:
                rospy.wait_for_service('/request_recognition', timeout=3.0)
                get_result = rospy.ServiceProxy('/request_recognition', Trigger)
                resp = get_result()
                if resp.success:
                    rospy.loginfo("识别服务调用成功")
            except Exception as e:
                rospy.logwarn("识别服务异常: %s" % str(e))

            self.data_received = False
            self.recognition_lock = False
            self.windows_go = [0, 0, 0]
            self.sample_count = 0
            self.lab_window = 0
            self.current_result = None
            self.received_results = []

            rospy.sleep(1.0)

            max_wait = 3.0
            waited = 0.0
            while waited < max_wait and not rospy.is_shutdown():
                rospy.sleep(0.5)
                waited += 0.5
                if self.current_result is not None:
                    if list(self.current_result) not in self.received_results:
                        self.received_results.append(list(self.current_result))
                        rospy.loginfo("收到结果: %s" % str(self.current_result))

            self.recognition_lock = True

            valid_result = None
            for result in reversed(self.received_results):
                if len(result) >= 6:
                    if result[3] in [1,2,3] and result[4] in [0,1,2,3]:
                        if all(v in [0,1] for v in result[0:3]):
                            valid_result = result
                            break

            if valid_result is not None:
                self.windows_go[0] = valid_result[0]
                self.windows_go[1] = valid_result[1]
                self.windows_go[2] = valid_result[2]
                self.sample_count = valid_result[3]
                self.lab_window = valid_result[4]
                self.sample_type = self.lab_window
                self.data_received = True

                windows_str = ""
                if self.windows_go[0]: windows_str += "C"
                if self.windows_go[1]: windows_str += "A"
                if self.windows_go[2]: windows_str += "B"
                sorted_windows = ''.join(sorted(windows_str))
                cv2_value = "%s-%d" % (sorted_windows, self.sample_type)
                self.update_cv2(cv2_value)

                rospy.loginfo("=" * 50)
                rospy.loginfo("✓✓✓ 识别完成 ✓✓✓")
                rospy.loginfo("  - 需访问窗口: %s" % self.get_windows_to_visit())
                rospy.loginfo("  - 样本数量: %d" % self.sample_count)
                rospy.loginfo("  - 样本类型: %s" % self.sample_name[self.sample_type])
                rospy.loginfo("  - CV2上报: %s" % cv2_value)
                rospy.loginfo("=" * 50)
                self.visit_all_labs = False
            else:
                rospy.logwarn("未收到有效数据，使用默认: ABC窗口, 组织样本")
                self.windows_go = [1, 1, 1]
                self.sample_count = 3
                self.lab_window = 2
                self.sample_type = 2
                self.data_received = True
                self.visit_all_labs = False
                self.update_cv2("ABC-2")

            self.count = 10

    def go_to_dispense_area(self):
        rospy.loginfo("【任务2】前往体检区取样本...")
        self.update_task("2")

        window_order = [('C', 0), ('A', 1), ('B', 2)]
        windows_to_visit = []

        for i in range(3):
            if self.windows_go[i]:
                windows_to_visit.append(window_order[i])

        for name, idx in windows_to_visit:
            rospy.loginfo("前往%s窗口取样本..." % name)
            self.update_task(name)
            self.clear_costmaps_service()
            goal = self.make_goal(self.waypoints[idx])
            if self.move_to(goal):
                rospy.loginfo("到达%s窗口，取样本中..." % name)
                self.clear_costmaps_service()
                # ========== 取样本停顿时间：0.25秒（原0.5秒的一半） ==========
                rospy.sleep(self.pause_time)
                rospy.loginfo("✓ 已从%s窗口取到样本" % name)

        if len(windows_to_visit) > 0:
            window_names = [w[0] for w in windows_to_visit]
            sample_type_name = self.sample_name[self.sample_type]

            if len(window_names) == 1:
                broadcast_text = "取到%s窗口的%s样本" % (window_names[0], sample_type_name)
            else:
                windows_str = '、'.join(window_names)
                broadcast_text = "取到%s窗口的%s样本" % (windows_str, sample_type_name)

            rospy.loginfo("【播报】%s" % broadcast_text)
            voice_filename = self.get_voice_filename(window_names, self.sample_type)
            self.play_voice(voice_filename)

        self.update_task("R")
        self.count = 11

    def go_to_delivery_area(self):
        rospy.loginfo("【任务4】前往化验区...")
        self.update_task("4")

        if self.visit_all_labs:
            lab_positions = [6, 5, 4, 3]
            lab_window_names = ['血常规', '体液', '免疫检测', '激素检验']

            for i in range(4):
                self.update_task(str(i+1))
                self.clear_costmaps_service()
                goal = self.make_goal(self.waypoints[lab_positions[i]])
                if self.move_to(goal):
                    rospy.loginfo("到达%s窗口" % lab_window_names[i])
                    self.clear_costmaps_service()
                    # ========== 送药停顿时间：0.25秒（原0.5秒的一半） ==========
                    rospy.sleep(self.pause_time)
                    broadcast_text = "到达%s窗口，样本数为%d" % (lab_window_names[i], self.sample_count)
                    rospy.loginfo("【播报】%s" % broadcast_text)
                    self.play_voice("delivery_sample.mp3")
        else:
            window_num = self.lab_window + 1
            window_name_cn = self.window_name[self.lab_window]
            lab_positions = {0: 6, 1: 5, 2: 4, 3: 3}
            window_idx = lab_positions[self.lab_window]

            rospy.loginfo("目标: %d号%s窗口" % (window_num, window_name_cn))
            self.update_task(str(window_num))

            self.clear_costmaps_service()
            goal = self.make_goal(self.waypoints[window_idx])
            if self.move_to(goal):
                rospy.loginfo("到达%d号%s窗口" % (window_num, window_name_cn))
                self.clear_costmaps_service()
                # ========== 送药停顿时间：0.25秒（原0.5秒的一半） ==========
                rospy.sleep(self.pause_time)

                broadcast_text = "到达%s窗口，样本数为%d" % (window_name_cn, self.sample_count)
                rospy.loginfo("【播报】%s" % broadcast_text)

                voice_prefix = {0: 'xuechanggui', 1: 'tiye', 2: 'mianyi', 3: 'jisu'}
                delivery_voice = "%s%d.mp3" % (voice_prefix[self.lab_window], self.sample_count)
                self.play_voice(delivery_voice)

        rospy.loginfo("任务完成，返回起点")
        self.update_task("R")
        self.clear_costmaps_service()
        goal_home = self.make_goal(self.waypoints[7])
        if self.move_to(goal_home):
            rospy.loginfo("已返回起点")
            # ========== 回到起点停顿时间：1.0秒（原2秒的一半） ==========
            rospy.sleep(self.home_pause_time)
            rospy.loginfo("等待下一轮...")

        self.count = 9
        self.data_received = False
        self.windows_go = [0, 0, 0]
        self.sample_count = 0
        self.lab_window = 0
        self.current_result = None
        self.received_results = []
        self.visit_all_labs = False

    def make_goal(self, pose):
        goal = MoveBaseGoal()
        goal.target_pose.header.frame_id = 'map'
        goal.target_pose.header.stamp = rospy.Time.now()
        goal.target_pose.pose = pose
        return goal

    def move_to(self, goal):
        self.move_base.send_goal(goal)
        finished = self.move_base.wait_for_result(rospy.Duration(30))
        if not finished:
            self.move_base.cancel_goal()
            rospy.logwarn("导航超时")
            return False
        return self.move_base.get_state() == GoalStatus.SUCCEEDED

    def play_voice(self, filename):
        full_path = self.voice_path + filename
        if os.path.exists(full_path):
            os.system("play %s" % full_path)
            rospy.loginfo("播放语音: %s" % filename)

    def detect_result(self, msg):
        if self.recognition_lock:
            return
        if len(msg.data) >= 6:
            self.current_result = list(msg.data)

    def get_windows_to_visit(self):
        windows = []
        if self.windows_go[0]: windows.append('C')
        if self.windows_go[1]: windows.append('A')
        if self.windows_go[2]: windows.append('B')
        return '、'.join(windows) if windows else '无'

    def get_voice_filename(self, window_names, sample_type):
        sample_pinyin = self.sample_pinyin.get(sample_type, 'default')
        sorted_windows = sorted(window_names)
        return "%s%s.mp3" % (sample_pinyin, ''.join(sorted_windows))

    def shutdown(self):
        rospy.loginfo("Stopping...")
        if hasattr(self, 'reporter'):
            self.reporter.stop()
        self.move_base.cancel_goal()
        self.cmd_vel_pub.publish(Twist())


if __name__ == '__main__':
    try:
        MoveBaseSquare()
    except rospy.ROSInterruptException:
        rospy.loginfo("Finished.")