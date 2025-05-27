#!/usr/bin/env pybricks-micropython

from pybricks.hubs import EV3Brick
from pybricks.parameters import Port, Direction, Stop
from pybricks.ev3devices import Motor, TouchSensor
from pybricks.tools import wait
from pybricks.media.ev3dev import SoundFile

from pybricks.messaging import BluetoothMailboxServer, TextMailbox

import json
import time
import threading
from collections import OrderedDict

#-------------------------------------------------------------------------
# Initialize the EV3.
ev3 = EV3Brick()

motorX = Motor(Port.B, positive_direction=Direction.COUNTERCLOCKWISE)
motorY = Motor(Port.D, positive_direction=Direction.COUNTERCLOCKWISE)
motorZ = Motor(Port.C, positive_direction=Direction.COUNTERCLOCKWISE)

touchSensorY = TouchSensor(Port.S1)
touchSensorX = TouchSensor(Port.S2)

#-------------------------------------------------------------------------

onePlate= 0.85

gearDiameter = 1.73
# gearPitchDiameter = 1.54

# pullCorrection = {"x": -0.025, "y": -0.1} #old
pullCorrection = {"x": 0, "y": -0.1} #working

# pushCorrection = {"x": 0.15, "y": -0.01} #old
pushCorrection = {"x": 0.1, "y": 0} #working

currCords = (-1000, -1000)

motorSpeed = 200

isPaused = False
refill = False

# adjustments = [
#         (motorX, 0, motorY, -0.1),
#         (motorX, -0.1, motorY, 0),
#         (motorX, 0, motorY, 0.1),
#         (motorX, 0, motorY, 0.1),
#         (motorX, 0.1, motorY, 0),
#         (motorX, 0.1, motorY, 0),
#         (motorX, 0, motorY, -0.1),
#         (motorX, 0, motorY, -0.1),
#         (motorX, -0.1, motorY, 0.1)
#     ]

# adjustments = [
#         (0, +0.1),
#         (0, -0.2),
#         (0, +0.1),
#         (+0.1, 0),
#         (-0.2, 0),
#         (+0.1, 0)
#     ]

# adjustments = [
#         (motorX, 0, motorY, 0.1),
#         (motorX, 0.1, motorY, 0),
#         (motorX, 0, motorY, -0.1),
#         (motorX, 0, motorY, -0.1),
#         (motorX, -0.1, motorY, 0),
#         (motorX, -0.1, motorY, 0),
#         (motorX, 0, motorY, 0.1),
#         (motorX, 0, motorY, 0.1),
#         (motorX, 0, motorY, 0.1),
#         (motorX, 0.1, motorY, 0),
#         (motorX, 0.1, motorY, 0),
#         (motorX, 0.1, motorY, 0),
#         (motorX, 0, motorY, -0.1),
#         (motorX, 0, motorY, -0.1),
#         (motorX, 0, motorY, -0.1),
#         (motorX, 0, motorY, -0.1),
#         (motorX, -0.1, motorY, 0),
#         (motorX, -0.1, motorY, 0),
#         (motorX, -0.1, motorY, 0),
#         (motorX, -0.1, motorY, 0),
#         (motorX, 0, motorY, 0.1),
#         (motorX, 0, motorY, 0.1),
#         (motorX, 0, motorY, 0.1),
#         (motorX, 0, motorY, 0.1)
#     ]

#-------------------------------------------------------------------------

def calculate_degree(cord, type=None, currentDegree=0):
    distance_cm = onePlate * cord

    scope = 3.14159265359 * gearDiameter
    rotations = distance_cm / scope
    degree = rotations * 360
    
    if type != None:
        if currentDegree > degree and (currCords[0] if type == 'x' else currCords[1]) != cord:
            # print(type + " pull")
            degree = calculate_degree(cord+pullCorrection[type])

        if currentDegree < degree and (currCords[0] if type == 'x' else currCords[1]) != cord:
            # print(type + " push")
            degree = calculate_degree(cord+pushCorrection[type])

    
    return degree

#calibration -------------------------------------------------------------

def calibrate_motorXY(motor, sensor):
    motor.run(-100)
    while not sensor.pressed():
        pass
    motor.brake()

    motor.run_time(100, 500)
    motor.run(-50)
    while not sensor.pressed():
        pass
    motor.brake()

def calibration():
    calibrate_motorXY(motorX, touchSensorX)
    calibrate_motorXY(motorY, touchSensorY)
    wait(1000)

    motorY.run_angle(50, calculate_degree(0.62), then=Stop.HOLD)
    motorX.run_angle(50, calculate_degree(0.15), then=Stop.HOLD)
    wait(1000)
    motorY.stop()
    motorX.stop()

    motorZ.run_until_stalled(500, then=Stop.HOLD, duty_limit=40)
    # motorZ.run_time(-500, 300)
    motorZ.run_time(-500, 550)
    wait(1000)
    motorZ.stop()

    motorX.reset_angle(0)
    motorY.reset_angle(0)
    motorZ.reset_angle(0)
    
#-------------------------------------------------------------------------

# def drive(cords):
#     global currCords

#     if currCords[1] != cords[1]:
#         # motorX.run_target(speed=motorSpeed, target_angle=calculate_degree(30, "x", motorX.angle()), then=Stop.HOLD) # for driving stability

#         motorY.run_target(speed=motorSpeed, target_angle=calculate_degree(cords[1], "y", motorY.angle()), then=Stop.HOLD)

#     if currCords[0] != cords[0]:
#         motorX.run_target(speed=motorSpeed, target_angle=calculate_degree(cords[0], "x", motorX.angle()), then=Stop.HOLD)

#     wait(1000)
#     # print("--------------------")
#     currCords = cords

def drive(cords):
    global currCords

    if currCords[1] != cords[1]:
        motorY.run_target(speed=motorSpeed, target_angle=calculate_degree(cords[1], "y", motorY.angle()), then=Stop.HOLD, wait=False)

    if currCords[0] != cords[0]:
        motorX.run_target(speed=motorSpeed, target_angle=calculate_degree(cords[0], "x", motorX.angle()), then=Stop.HOLD)

    while motorY.speed() != 0:
        wait(100)
    
    wait(1000)
    currCords = cords

#-------------------------------------------------------------------------

def pickup():
    motorZ.run_until_stalled(400, then=Stop.HOLD, duty_limit=40)
    # angleZ = motorZ.angle()

    motorZ.run_target(400, 0)
    motorZ.stop()

    # for adj in adjustments:
    #     motor1, angle1, motor2, angle2 = adj
    #     print(angleZ)

    #     if angleZ >= -190:
    #         motor1.run_angle(800, calculate_degree(angle1), then=Stop.HOLD)
    #         motor2.run_angle(800, calculate_degree(angle2), then=Stop.HOLD)

    #         motorZ.run_until_stalled(400, then=Stop.HOLD, duty_limit=40)
    #         angleZ = motorZ.angle()
    #         motorZ.run_target(400, 0)
    #     else:
    #         break        


def place():
    # if (ev3.battery.voltage() >= 7500):
    #     place_dl = 40
    # else:
    #     place_dl = 50

    place_dl = 60
    test_dl = 31

    # motorZ.run_until_stalled(50, then=Stop.HOLD, duty_limit=test_dl)
    # angleZ = motorZ.angle()
    motorZ.run_target(200, 0)

    # print(angleZ)

    # if angleZ <= 90:
    #     print("ERROR")

    #     for adj in adjustments:
    #         angleX, angleY = adj
    #         print(angleZ)

    #         if angleZ <= 90:
    #             if angleX != 0:
    #                 motorX.run_angle(motorSpeed, calculate_degree(angleX, "x", motorX.angle()), then=Stop.HOLD)

    #             if angleY != 0:
    #                 motorY.run_angle(motorSpeed, calculate_degree(angleY, "y", motorY.angle()), then=Stop.HOLD)

    #             wait(1000)

    #             motorZ.run_until_stalled(50, then=Stop.HOLD, duty_limit=test_dl)
    #             angleZ = motorZ.angle()
    #             motorZ.run_target(200, 0)
    #         else:
    #             break

    #         print("--------------------")

    motorZ.run_until_stalled(400, then=Stop.HOLD, duty_limit=place_dl)
    motorZ.run_target(500, 0)
    wait(1000)
    motorZ.stop()           

#-------------------------------------------------------------------------

def run(lego, mbox):
    recalibration = False
    colorCords = {
        "black": (20,33),
        "dark_bluish_grey": (22,33),
        "light_bluish_grey": (24,33),
        "white": (26,33)
    }

    for cord, color in lego.items():
        while isPaused:
            ev3.screen.clear()
            ev3.screen.draw_text(10, 10, "Paused")
            if refill:
                ev3.screen.draw_text(10, 40, "Refill all colours.")

            if recalibration == False:
                recalibration = True
                calibration()
            time.sleep(1)

        recalibration = False
        cord = cord.split(",")

        ev3.screen.clear()
        ev3.screen.draw_text(10, 10, str((int(cord[0]), int(cord[1]))))
        ev3.screen.draw_text(10, 40, str(color).upper())

        drive(colorCords[color])

        pickup()
        
        drive((int(cord[0]), int(cord[1])))
        
        place()

        mbox.send(cord)
        mbox.send(color)

    drive((0,0))
    mbox.send("finished")
    
def test():
     
    calibration()

    # drive((31,31))
    # pickup()
    # wait(6000)
    # drive((0,0))
    # pickup()

    # for i in range(0, 31):
    #     drive((i, i))
    #     pickup()
    #     drive((0,0))
    #     pickup()

    # import random
    # while True:
    #     x = random.randint(0, 31)
    #     y = random.randint(0, 31)
    #     drive((x, y))
    #     pickup()


    drive((20,33))
    pickup()
    drive((1,1))
    place()


    drive((22,33))
    pickup()
    drive((2,2))
    place()

    drive((24,33))
    pickup()
    drive((3,3))
    place()

    drive((26,33))
    pickup()
    drive((4,4))
    place()


#-------------------------------------------------------------------------

def receiveMessages(mbox):
    global isPaused
    global refill

    while True:
        mbox.wait()
        msg = mbox.read()

        if msg == "pause":
            isPaused = True
            ev3.speaker.play_file(SoundFile.GENERAL_ALERT)
        elif msg == "resume":
            isPaused = False
            refill = False
        elif msg == "refill":
            isPaused = True
            refill = True
            ev3.speaker.play_file(SoundFile.GENERAL_ALERT)

#-------------------------------------------------------------------------

# test()

ev3.speaker.set_volume(10)
ev3.speaker.beep(500)
ev3.speaker.beep(700)
ev3.speaker.beep(900)

server = BluetoothMailboxServer()
mbox = TextMailbox("pixel", server)

server.wait_for_connection()

mbox.wait()

lego = mbox.read()
lego = lego.replace("'", '"')
lego = json.loads(lego, object_pairs_hook=OrderedDict)

ev3.speaker.play_file(SoundFile.CONFIRM)
mbox.send("received lego data")

calibration()

ev3.speaker.play_file(SoundFile.READY)
mbox.send("ready")
mbox.wait()

msg = mbox.read()
if msg == "run":
    ev3.speaker.set_volume(100)
    threading.Thread(target=receiveMessages, args=(mbox,)).start()
    run(lego, mbox)
