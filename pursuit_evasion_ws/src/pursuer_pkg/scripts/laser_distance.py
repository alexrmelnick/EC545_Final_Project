#!/usr/bin/env python
# coding:utf-8
import math
import numpy as np
from common import *
from std_msgs.msg import Bool
from sensor_msgs.msg import LaserScan
from dynamic_reconfigure.server import Server
from yahboomcar_laser.cfg import laserTrackerPIDConfig
import random
RAD2DEG = 180 / math.pi

class laserDistance:
    def __init__(self):
        rospy.on_shutdown(self.cancel)
        self.Moving = False
        self.switch = False
        self.ros_ctrl = ROSCtrl()
        self.lin_pid = SinglePID(2.0, 0.0, 2.0)
        self.ang_pid = SinglePID(3.0, 0.0, 5.0)
        self.ResponseDist = rospy.get_param('~targetDist', 0.25)
        Server(laserTrackerPIDConfig, self.dynamic_reconfigure_callback)
        self.laserAngle = 90
        self.priorityAngle = 30  # 40
        self.sub_laser = rospy.Subscriber('/scan', LaserScan, self.registerScan, queue_size=1)
        self.pub_dist = rospy.Publisher('/Laser_Distance', Int, queue_size=1)

    def cancel(self):
        self.ros_ctrl.pub_vel.publish(Twist())
        self.ros_ctrl.cancel()
        self.sub_laser.unregister()
        rospy.loginfo("Shutting down this node.")

    def registerScan(self, scan_data):
        if not isinstance(scan_data, LaserScan): return
        # Record the laser scan and publish the position of the nearest object (or point to a point)
        ranges = np.array(scan_data.ranges)
        offset = 0.5
        frontDistList = []
        frontDistIDList = []
        minDistList = []
        minDistIDList = []
        # if we already have a last scan to compare to:
        for i in range(len(ranges)):
            angle = (scan_data.angle_min + scan_data.angle_increment * i) * RAD2DEG
            # if angle > 90: print "i: {},angle: {},dist: {}".format(i, angle, scan_data.ranges[i])
            if abs(angle) > (180 - self.priorityAngle): #If greater than 150 (Right side to left side 30 degrees)
                if ranges[i] < (self.ResponseDist + offset):
                    frontDistList.append(ranges[i])
                    frontDistIDList.append(angle)
            elif (180 - self.laserAngle) < angle < (180 - self.priorityAngle): #If Between 90-150
                minDistList.append(ranges[i])
                minDistIDList.append(angle)
            elif (self.priorityAngle - 180) < angle < (self.laserAngle - 180): #If between -150 and -90
                minDistList.append(ranges[i])
                minDistIDList.append(angle)
        # Find the minimum distance and the ID corresponding to the minimum distance
        if len(frontDistIDList) != 0: #uses min distance in front of it
            minDist = min(frontDistList)
            minDistID = frontDistIDList[frontDistList.index(minDist)]
        else:
            minDist = min(minDistList)
            minDistID = minDistIDList[minDistList.index(minDist)]
        rospy.loginfo('minDist: {}, minDistID: {}'.format(minDist, minDistID))
        self.pub_dist.publish(minDist) # Publish the minimum distance



        
#         if self.ros_ctrl.Joy_active or self.switch == True:
#             if self.Moving == True:
#                 self.ros_ctrl.pub_vel.publish(Twist())
#                 self.Moving = not self.Moving
#             return
#         self.Moving = True
#         velocity = Twist()
#         
#         if abs(minDist - self.ResponseDist) < 0.1: 
#             minDist = self.ResponseDist
#             
#         velocity.linear.x = -self.lin_pid.pid_compute(self.ResponseDist, minDist)
#         
#         ang_pid_compute = self.ang_pid.pid_compute((180 - abs(minDistID)) / 72, 0)
#         
#         if minDistID > 0: 
#             velocity.angular.z = -ang_pid_compute
#         else: 
#             velocity.angular.z = ang_pid_compute
#         if ang_pid_compute < 0.2: 
#             velocity.angular.z = 0
#         
#         # rospy.loginfo('minDistID: {},ang_pid_compute: {}'.format(minDistID,ang_pid_compute))
#         #rospy.loginfo('minDist: {}, linearX: {}'.format(minDist, velocity.linear.x))
#         #rospy.loginfo('minDistID: {}, angularSpeed: {}'.format(minDistID, velocity.angular.z))
# 
#         wallCheck = np.array(frontDistList)
#         wallCheck = wallCheck[np.isfinite(wallCheck)]
#         grad1 = np.gradient(wallCheck)
#         grad2 = np.gradient(grad1)
#         maxg2 = max(grad2)
#         ming2 = min(grad2)
#         rospy.loginfo(grad2)
#         rospy.loginfo(maxg2)
#         rospy.loginfo(ming2)
# 
#         if velocity.linear.x == 0 and maxg2 > 0.015 and ming2 < -0.015:
#             #service call to pause chase for 10s and  tick up pursuer win counter
#             rospy.loginfo("Robot Captured")
#             pass
#         elif velocity.linear.x == 0:
#             rospy.loginfo("This is a wall")
#             velocity.angular.z = 1
#         
#         self.ros_ctrl.pub_vel.publish(velocity)

    def dynamic_reconfigure_callback(self, config, level):
        self.switch = config['switch']
        self.laserAngle = config['laserAngle']
        self.priorityAngle = config['priorityAngle']
        self.ResponseDist = config['ResponseDist']
        self.lin_pid.Set_pid(config['lin_Kp'], config['lin_Ki'], config['lin_Kd'])
        self.ang_pid.Set_pid(config['ang_Kp'], config['ang_Ki'], config['ang_Kd'])
        return config


if __name__ == '__main__':
    rospy.init_node('laser_Tracker', anonymous=False)
    tracker = laserTracker()
    rospy.spin()
