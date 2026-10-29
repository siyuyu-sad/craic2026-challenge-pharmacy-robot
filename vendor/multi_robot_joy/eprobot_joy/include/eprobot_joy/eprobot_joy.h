#ifndef __EPROBOT_JOY_H__
#define __EPROBOT_JOY_H__

#include <stdio.h>
#include "ros/ros.h"
#include <iostream>
#include <math.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <unistd.h>
#include <serial/serial.h>
#include <stdbool.h>
#include <tf/transform_broadcaster.h>
#include <std_msgs/String.h>
#include <geometry_msgs/Twist.h>

using namespace std;

#define JS_EVENT_BUTTON         0x01        /* button pressed/released */
#define JS_EVENT_AXIS           0x02        /* joystick moved */
#define JS_EVENT_INIT           0x80        /* initial state of device */
#define JS_EVENT_BUTTON_DOWN    0X01

#define JS_MODE_1				1
#define JS_MODE_2				2	

#define EN_1                    0x01
#define EN_2                    0x02
#define EN_3                    0x04
#define EN_ALL                  0x07
#define DIS_ALL                 0x00

struct js_event {
    unsigned int time;      /* event timestamp in milliseconds */
    short value;            /* value */
    unsigned char type;     /* event type */
    unsigned char number;   /* axis/button number */
};

class eprobot_joy{

private:

    int leftHorizontal, leftVertical, rightHorizontal, rightVertical;
    int joystick_fd,joystick_mode;
    float maxLinear_x, maxLinear_y, maxAngular_z;
    string joystick_device;
	string pub_topic,pub_topic1,pub_topic2;
	unsigned char pub_en;
    struct js_event jse;
    ros::NodeHandle n;
    ros::Publisher cmd_vel_pub,cmd_vel_pub1,cmd_vel_pub2;
    geometry_msgs::Twist vel_msg_;

public:
    eprobot_joy();
    ~eprobot_joy();
    void publish_joystick_event();
    void joystick_process();
};

#endif