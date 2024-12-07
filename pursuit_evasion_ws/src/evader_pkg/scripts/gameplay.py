#!/usr/bin/env python
# coding:utf-8
import time
from common import *
from time import sleep, time
from std_msgs.msg import String

class gamePlay:
    def __init__(self):
        rospy.on_shutdown(self.cancel)
        self.r = rospy.Rate(20)
        #self.ros_ctrl = ROSCtrl()
        self.wait_time = 5
        self.pursuer_wait = 10
        self.evade_points = 0
        self.pursuer_points = 0
        self.reset=False
        self.start_time = time()
        self.sub_pursuit = rospy.Subscriber('/caught', Bool, self.restartGame, queue_size=1)
        self.pub_evader = rospy.Publisher('/evader', Bool, queue_size=1)
        self.pub_pursuer = rospy.Publisher('/pursuer', Bool, queue_size=1)
        self.pub_points = rospy.Publisher('/points', String, queue_size=1)
        self.sub_reset = rospy.Subscriber('/reset',Bool,self.reset_callback,queue_size=1)

    def cancel(self):
        #self.ros_ctrl.pub_vel.publish(Twist())
        #self.ros_ctrl.cancel()
        self.sub_pursuit.unregister()
        rospy.loginfo("Shutting down this node.")

    def reset_callback(self,reset_signal):
        if not isinstance(reset_signal, Bool): return
        self.reset=reset_signal.data

    def restartGame(self, caught_signal):
        if not isinstance(caught_signal, Bool): return

        # tell pursuer to wait
        self.pub_evader.publish(False)
        # tell evader to wait
        self.pub_pursuer.publish(False)

        # Pursuer caught evader
        if caught_signal.data == True:
            # update score: +1 for pursuer
            if self.reset:
                self.pursuer_points =0
                self.evade_points=0
                self.reset=False
                self.pub_points.publish("Pursuer: "+str(self.pursuer_points)+"\nEvader: "+str(self.evade_points))
                
            else:
                self.pursuer_points += 1
                self.pub_points.publish("Pursuer: "+str(self.pursuer_points)+"\nEvader: "+str(self.evade_points))

        # Evader survived 30 seconds
        else:
            # update score: +1 for evader
            if self.reset:
                self.pursuer_points =0
                self.evade_points=0
                self.reset=False
                self.pub_points.publish("Pursuer: "+str(self.pursuer_points)+"\nEvader: "+str(self.evade_points))
            else:
                self.evade_points += 1
                self.pub_points.publish("Pursuer: "+str(self.pursuer_points)+"\nEvader: "+str(self.evade_points))

        # wait 5 seconds
        sleep(self.wait_time)
        # tell evader to go
        self.pub_evader.publish(True)
        # wait 10 seconds
        sleep(self.pursuer_wait)
        # tell pursuer to go
        self.pub_pursuer.publish(True)
        self.start_time = time()


if __name__ == '__main__':
    rospy.init_node('gameplay', anonymous=False)
    game = gamePlay()
    rospy.spin()
    '''end_time = time()
    while(True):
        if (end_time - game.start_time) > 30:
            game.restartGame(Bool(False))
        end_time = time()'''
