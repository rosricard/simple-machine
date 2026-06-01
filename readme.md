# Problem statement:
Build a small machine that does robotic pick and place

# Input
How do you receive inputs from orchestration system? There's a manual and auto mode but the interface can be shared. However, manual mode itself will likely have different requirements.
Could make some assumptions that the interface will be compiled into a json data structure. Create an interface that allows the robot to do one of 3 different pick and place tasks.

# Main Controller - Event Driven Layer
This is the event driven layer that handles the system state. Overall states will be Abort, Home, Start. It also needs to handle the commands being sent to the robot.

Suggest and of the following that would be relevant to include for control of a robot doing a point to point pick and place application:
- Any relevant robotic theory
is it relevant to include any of the following? 
- Jacobians 
- Inverse kinematics
- Basic fundamentals
- Manipulation frame
- User frame
- Tool frame
- Tool centerpoint

# Signal Repository
This is the repository that interfaces with the robot and will send the trajectory command.
this should be built with an interface that would allow hardware abstraction so that the application can be hardware agnostic (ex: Fanuc vs Kuka). Beyond defining simply an interface, also define a 

# Out of scope for this assignment - Actuation layer

This layer needs to be more deterministic (if kept in python it would been to have some sort of async IO to deal with the python GIL because we can't get the same speed or determinism that you could with an RTOS).
For the purposes of this interview, we'll 

# Control Device library 
Library of HALs that would be designed with interfaces to keep the code base vendor agnostic

# Mock bot
so that we can do SIL testing of our application and not require hardware. This would be a separate async process that would run to emulate the hardware 


# Assumptions 
1. the task options being sent are parametrized by source / target post (or do we want a hard coded routine?)
2. Orchestration layer speaks json over the pub/sub bus (MQTT or NATs)?
3. Vendor controller handles the trajectory generation and inverse kinematics; this app will handle cartesian goals
4. assuming single arm, single gripper
5. this layer is event driven - no hard real time requirement
6. manual vs auto differ in command source and cadence and not schema

