#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OCR识别节点 —— 识别板2文字识别（白底黑字 + 两行文本优化版）
"""
import cv2
import pytesseract
import re
import rospy
from std_msgs.msg import Int32MultiArray, String
import platform

if platform.system() == 'Windows':
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
ROI_REGION = (100, 150, 600, 424)  # 根据实际调整

FREE_KEYWORDS = ['空闲', '通过']
BUSY_KEYWORDS = ['忙碌', '等待']

STATS = {"total": 0, "success": 0, "fail": 0}


def preprocess_image(img, roi_region):
    x1, y1, w, h = roi_region
    h_img, w_img = img.shape[:2]
    x1 = max(0, x1); y1 = max(0, y1)
    w = min(w, w_img - x1); h = min(h, h_img - y1)

    roi = img[y1:y1+h, x1:x1+w]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    denoised = cv2.GaussianBlur(gray, (3, 3), 0)
    # 自适应阈值适合白底黑字，保留两行文字的清晰度
    binary = cv2.adaptiveThreshold(denoised, 255,
                                   cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    return roi, binary


def recognize_text(img_binary):
    """针对两行文本：PSM=6（块文本模式）"""
    config = '--oem 3 --psm 6 -l chi_sim'
    raw = pytesseract.image_to_string(img_binary, config=config)
    text = re.sub(r'[\s\n\t\r]', '', raw)
    confidence = 0.8 if text else 0.0
    return text, confidence


def parse_result(text):
    if not text:
        return False, 0
    is_free = any(kw in text for kw in FREE_KEYWORDS)
    is_busy = any(kw in text for kw in BUSY_KEYWORDS)
    if is_free and not is_busy:
        return False, 0
    if is_busy:
        m = re.search(r'(\d+)\s*秒', text)
        if m:
            n = int(m.group(1))
            if 5 <= n <= 10:
                return True, n
        m = re.search(r'(\d+)', text)
        if m:
            n = int(m.group(1))
            if 5 <= n <= 10:
                return True, n
        return True, 8
    return False, 0


def main():
    rospy.init_node('ocr_board2', anonymous=True)
    pub_result = rospy.Publisher('/board2_result', Int32MultiArray, queue_size=5)
    pub_text = rospy.Publisher('/board2_text', String, queue_size=5)

    camera_idx = rospy.get_param('~camera_index', CAMERA_INDEX)
    roi = rospy.get_param('~roi', list(ROI_REGION))
    roi = (int(roi[0]), int(roi[1]), int(roi[2]), int(roi[3]))
    headless = rospy.get_param('~headless', False)

    cap = cv2.VideoCapture(camera_idx)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    if not cap.isOpened():
        rospy.logerr("[OCR] 无法打开摄像头")
        return

    rospy.loginfo("[OCR] 两行文本优化版启动 | ROI: %s", roi)
    rate = rospy.Rate(10)

    while not rospy.is_shutdown():
        ret, frame = cap.read()
        if not ret:
            rate.sleep()
            continue

        roi_img, img_binary = preprocess_image(frame, roi)
        try:
            text, confidence = recognize_text(img_binary)
        except Exception as e:
            rospy.logerr("[OCR] Tesseract异常: %s", e)
            rate.sleep()
            continue

        STATS["total"] += 1
        if text:
            is_busy, wait_time = parse_result(text)
            STATS["success"] += 1
            pub_result.publish(Int32MultiArray(data=[1 if is_busy else 0, wait_time]))
            pub_text.publish(String(data=text))
            status = "BUSY(%ds)" % wait_time if is_busy else "FREE"
            rospy.loginfo("[OCR] %s | 原文=%s", status, repr(text))
        else:
            STATS["fail"] += 1
            if STATS["fail"] % 30 == 1:
                rospy.logwarn("[OCR] 未识别到文字 (失败: %d)", STATS["fail"])

        if not headless:
            x1, y1, w, h = roi
            cv2.rectangle(frame, (x1, y1), (x1+w, y1+h), (0,255,0), 2)
            cv2.putText(frame, text if text else "(未识别)", (20,40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,0), 2)
            cv2.imshow("OCR - ROI Binary", img_binary)
            cv2.imshow("OCR - Main", frame)
            key = cv2.waitKey(1) & 0xFF
            if key == 27: break
            elif key == ord('s'):
                ts = rospy.Time.now().to_sec()
                cv2.imwrite("ocr_frame_%.0f.jpg" % ts, frame)
                cv2.imwrite("ocr_binary_%.0f.jpg" % ts, img_binary)
                rospy.loginfo("截图已保存")

        rate.sleep()

    cap.release()
    cv2.destroyAllWindows()
    rospy.loginfo("[OCR] 停止 | 成功率: %d/%d", STATS["success"], STATS["total"])


if __name__ == "__main__":
    main()