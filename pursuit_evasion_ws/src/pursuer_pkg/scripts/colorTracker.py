#!/usr/bin/env python
# coding: utf-8
import time
import rospy
import cv2 as cv
from astra_common import simplePID
from cv_bridge import CvBridge
from std_msgs.msg import Bool
from std_msgs.msg import Int32, Float32
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
from yahboomcar_msgs.msg import Position
from dynamic_reconfigure.server import Server
from yahboomcar_astra.cfg import ColorTrackerPIDConfig
from Rosmaster_Lib import Rosmaster
from common import *

class color_Tracker:
    def __init__(self):
        rospy.on_shutdown(self.cleanup)
        self.bot = Rosmaster()
        self.ros_ctrl = ROSCtrl()
        self.r = rospy.Rate(50)
        self.bridge = CvBridge() # ROS to OpenCV 
        self.minDist = 500 # 0.5m minimum distance
        self.Center_x = 0 # X Pixel of detected object 
        self.Center_y = 0 # Y Pixel of detected object
        self.Center_r = 0 # Radius of detection of object
        self.Center_prevx = 0 
        self.Center_prevr = 0
        self.prev_time = 0
        self.prev_dist = 0
        self.prev_angular = 0
        self.Robot_Search = False
        self.new_Search = True
        self.go = True
        self.timer30_prev = time.time()
        self.dist = []
        self.runList = [0]
        # self.Laser_Distance = 0
        self.encoding = ['16UC1', '32FC1'] # Depth image encoding
        self.sub_game = rospy.Subscriber("/pursuer", Bool, self.on_off, queue_size = 1)
        self.sub_depth = rospy.Subscriber("/camera/depth/image_raw", Image, self.depth_img_Callback, queue_size = 1) # Subscribe to depth image
        self.sub_position = rospy.Subscriber("/Current_point", Position, self.positionCallback, queue_size = 1) # Subscribe to data returned from ColorHSV Program
        self.sub_laser_distance = rospy.Subscriber("/Laser_Dist", Bool, self.laserDistCallback, queue_size = 1)
        self.pub_captured = rospy.Publisher("/caught", Bool, queue_size=1)
        #self.pub_cmdVel = rospy.Publisher('/cmd_vel', Twist, queue_size=10) # Publishes velocity to Yahboom
        Server(ColorTrackerPIDConfig, self.AstraFollowPID_callback) # PID Configuration
        self.linear_PID = (3.0, 0.0, 1.0)
        self.angular_PID = (0.5, 0.0, 2.0)
        self.scale = 1000 # Scale because depth camera is in mm
        self.PID_init()

    def on_off(self, game_signal):
        if not isinstance(game_signal, Bool): return
        self.go = game_signal.data
        if not game_signal.data:
            self.ros_ctrl.pub_vel.publish(Twist())
        else:
            self.timer30_prev = time.time()

    def AstraFollowPID_callback(self, config, level): # PID Initialization
        self.linear_PID = (config['linear_Kp'], config['linear_Ki'], config['linear_Kd'])
        self.angular_PID = (config['angular_Kp'], config['angular_Ki'], config['angular_Kd'])
        #self.minDist = config['minDist'] * 1000
        print ("linear_PID: ", self.linear_PID)
        print ("angular_PID: ", self.angular_PID)
        self.PID_init()
        return config

    def PID_init(self): # PID Initialization
        self.linear_pid = simplePID(self.linear_PID[0] / 1000.0, self.linear_PID[1] / 1000.0, self.linear_PID[2] / 1000.0)
        self.angular_pid = simplePID(self.angular_PID[0] / 100.0, self.angular_PID[1] / 100.0, self.angular_PID[2] / 100.0)

    def depth_img_Callback(self, msg):
        if not isinstance(msg, Image): # Skip if no depth image available
            return
        if self.go:
            depthFrame = self.bridge.imgmsg_to_cv2(msg, desired_encoding=self.encoding[1]) # Convert image to depth image for OpenCV to read
            self.action = cv.waitKey(1)
            now_time = time.time()
            #rospy.loginfo(self.Laser_Distance)
            if now_time - self.timer30_prev > 30:
                # do we want to put an LED color here?
                self.bot.set_colorful_lamps(0xff, 128, 0, 128)
                self.pub_captured.publish(False)
                self.timer30_prev = now_time
                self.new_Search = True
                self.runList = []
            elif self.Laser_Distance == True:
                twistRev = Twist()
                twistRev.linear.x = -0.5
                self.ros_ctrl.pub_vel.publish(twistRev)
                self.new_Search = True
                self.runList = []
                self.bot.set_colorful_lamps(0xff, 0, 255, 0) #Set LED to green to indicate lidar takeover
                self.r.sleep()
            elif self.Center_r != 0 and 50 < int(self.Center_y - 3) and int(self.Center_y + 3) < 480: # If something is detected, run this if statement
                if now_time - self.prev_time > 5: # If 5ms go by and nothing has changed, assume nothing is detected and radius = 0
                    if self.Center_prevx == self.Center_x and self.Center_prevr == self.Center_r: 
                        self.Center_r = 0
                    self.prev_time = now_time
                distance = [0, 0, 0, 0, 0]
                if 50 < int(self.Center_y - 3) and int(self.Center_y + 3) < 480 and 0 < int(self.Center_x - 3) and int(self.Center_x + 3) < 640: # If object is in frame
                    # print("depthFrame: ", len(depthFrame), len(depthFrame[0]))
                    distance[0] = depthFrame[int(self.Center_y - 2)][int(self.Center_x - 2)] # Calculate an array of distances around the center point of object
                    distance[1] = depthFrame[int(self.Center_y + 2)][int(self.Center_x - 2)] # Offset by 3 pixels
                    distance[2] = depthFrame[int(self.Center_y - 2)][int(self.Center_x + 2)]
                    distance[3] = depthFrame[int(self.Center_y + 2)][int(self.Center_x + 2)]
                    distance[4] = depthFrame[int(self.Center_y)][int(self.Center_x)]
                    distance_ = 0
                    num_depth_points = 5
                    for i in range(5):
                        if 40 < distance[i] < 8000: 
                            distance_ += distance[i] # Adds up distances as long as they're between 40-8000mm
                        else: 
                            num_depth_points -= 1
                    if num_depth_points == 0: 
                        distance_ = self.prev_dist # Assumes object is 0.5m away when nothing detected
                    else: 
                        distance_ = int(distance_/num_depth_points) # Calculates avg distance to target to send to PID velocity controller
                    #print("Center_x: {}, Center_y: {}, distance_: {}".format(self.Center_x, self.Center_y, distance_))
                    #distance_ = depthFrame[int(self.Center_y)][int(self.Center_x)]
                    if len(self.runList) < 5:
                        self.runList.insert(0, distance_)
                        runAvg = sum(self.runList) / len(self.runList)
                        return
                    else:
                        self.runList.insert(0, distance_)
                        self.runList.pop()
                        runAvg = sum(self.runList) / 5
                    if 40 < distance_ < 8000 and abs(distance_ - runAvg) < 500:
                        pass
                    else:
                        distance_ = runAvg
                    self.controller(self.Center_x, distance_) #Sends the x pixel location and avg distance to be converted to PID speed commands
                    self.Center_prevx = self.Center_x
                    self.Center_prevr = self.Center_r
                    self.prev_dist = distance_
                    distance_ = 0
                    #self.prev_angular = self.Center_x
                    self.r.sleep()
                else:
                    self.bot.set_colorful_lamps(0xff, 255, 255, 0) #Set LED to yellow to indicate search state
                    twistSearch = Twist()
                    twistSearch.linear.x = 0
                    twistSearch.angular.z = 1
                    self.ros_ctrl.pub_vel.publish(twistSearch) # Robot spins to search for red
                    self.new_Search = True
                    self.runList = []
                    self.r.sleep()
                    #rospy.loginfo(runAvg)
            else:
                self.bot.set_colorful_lamps(0xff, 255, 255, 0) #Set LED to yellow to indicate search state
                twistSearch = Twist()
                twistSearch.linear.x = 0
                twistSearch.angular.z = 1
                self.ros_ctrl.pub_vel.publish(twistSearch) # Robot spins to search for red
                self.new_Search = True
                self.runList = []
                self.r.sleep()
            if self.action == ord('q') or self.action == 113: 
                self.cleanup()
            #cv.imshow("depth_img", depthFrame)

    def controller(self, point_x, dist):
        if self.new_Search == True:
            self.new_Search = False
        else:
            if abs(self.prev_dist - dist) > 300: # Keeps the program locked onto one target so it doesn't jump to any other random color detected
                self.prev_dist = dist
                return
            if abs(self.prev_angular - point_x) > 100:
                self.prev_angular = point_x
                return
        if abs(dist - self.minDist) < 100: 
            linear_x = 0
            angular_z = 0
            twist = Twist()
            twist.angular.z = angular_z
            twist.linear.x = linear_x
            self.bot.set_colorful_lamps(0xff, 0, 0, 255) #Set lamps to blue and pause program when captured other bot
            self.ros_ctrl.pub_vel.publish(twist)
            rospy.loginfo("dist: {}, runList: {}".format(dist, self.runList))
            self.new_Search = True
            self.runList = []
            self.prev_dist = 2000
            self.Center_r = 0
            self.pub_captured.publish(True)
            return
        else:
            self.bot.set_colorful_lamps(0xff, 255, 0, 0) #Set lamps to red
            linear_x = self.linear_pid.compute(dist, self.minDist)
            angular_z = self.angular_pid.compute(320, point_x)
            if abs(point_x - 320.0) < 30: 
                angular_z = 0
            twist = Twist()
            twist.angular.z = angular_z / 2
            twist.linear.x = linear_x / 7
            self.ros_ctrl.pub_vel.publish(twist)
            rospy.loginfo("dist: {}, linear_x: {}, angular_z: {}".format(dist, twist.linear.x, twist.angular.z))
            return

    def positionCallback(self, msg): #Calls colorHSV function to get color tracking info from camera
        if not isinstance(msg, Position): 
            return
        self.Center_x = msg.angleX
        self.Center_y = msg.angleY
        self.Center_r = msg.distance

    def laserDistCallback(self, minDist):
        self.Laser_Distance = minDist.data
        # self.Laser_Distance = self.Laser_Distance * Float32(1000)

    def cleanup(self): #Closes and cleans up program and nodes
        #self.pub_cmdVel.publish(Twist())
        self.sub_depth.unregister()
        self.sub_position.unregister()
        self.sub_laser_distance.unregister()
        self.sub_game.unregister()
        self.pub_captured.unregister()
        #self.pub_cmdVel.unregister()
        print ("Shutting down this node.")
        cv.destroyAllWindows()

if __name__ == '__main__':
    rospy.init_node("color_Tracker", anonymous=False)
    color_Tracker()
    rospy.spin()
    
