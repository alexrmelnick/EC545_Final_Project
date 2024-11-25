#!/usr/bin/env python
import rospy
from turtlesim.msg import Pose

def pose_callback(msg):
    rospy.loginfo("(" + str(msg.x) + ", " + str(msg.y) + ")")
if __name__ == '__main__':
    rospy.init_node("turtle_pose_sub")

    sub = rospy.Subscriber("/turtle1/pose",Pose,callback=pose_callback)

    rospy.loginfo("node started")
    rospy.spin()
