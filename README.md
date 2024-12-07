# Pursuit Evasion Project: EC 545 Cyber-Physical Systems
## Instructions
1. ssh into evader robot
2. Run 'roslaunch evader_pkg laser_Avoidance_evader.launch'
3. To run with a joystick: run 'roslaunch evader_pkg laser_Avoidance_joy.launch' instead

4. ssh into pursuer robot
5. Run 'roslaunch pursuer_pkg colorTracker.launch VideoSwitch:=False' in one terminal
6. Run 'roslaunch pursuer_pkg colorHSV.launch' in another terminal
7. To see the score: run 'rostopic echo /points' in a third terminal
