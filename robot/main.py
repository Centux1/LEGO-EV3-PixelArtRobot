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

motorX = Motor(Port.D, positive_direction=Direction.COUNTERCLOCKWISE)
motorY = Motor(Port.A, positive_direction=Direction.COUNTERCLOCKWISE)
motorZ = Motor(Port.C)

touchSensorY = TouchSensor(Port.S1)
touchSensorX = TouchSensor(Port.S2)

#-------------------------------------------------------------------------

onePlate= 0.85

gearDiameter = 1.73
# gearPitchDiameter = 1.54

# pullCorrection = {"x": -0.09, "y": -0.14}
pullCorrection = {"x": -0.025, "y": -0.1} #working
# pullCorrection = {"x": -0.025, "y": -10}

motorSpeed = 200

isPaused = False
refill = False

#-------------------------------------------------------------------------

def calculate_degree(cord, type="x", currentDegree=-10000):
    distance_cm = onePlate * cord

    volume = 3.14159265359 * gearDiameter
    rotations = distance_cm / volume
    degree = rotations * 360

    if currentDegree > degree:
        print(pullCorrection)
        degree = calculate_degree(cord+pullCorrection[type])

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
    motorX.run_angle(50, calculate_degree(1.136), then=Stop.HOLD)
    wait(1000)
    motorY.stop()
    motorX.stop()

    motorZ.run_until_stalled(-800, then=Stop.HOLD, duty_limit=40)
    # motorZ.run_time(500, 300)
    motorZ.run_time(500, 550)
    wait(1000)
    motorZ.stop()

    motorX.reset_angle(0)
    motorY.reset_angle(0)
    motorZ.reset_angle(0)
    
#-------------------------------------------------------------------------

def drive(cords):
    motorY.run_target(speed=motorSpeed, target_angle=calculate_degree(cords[1], "y", motorY.angle()), then=Stop.HOLD)
    motorX.run_target(speed=motorSpeed, target_angle=calculate_degree(cords[0], "x", motorX.angle()), then=Stop.HOLD)
    wait(1000)

#-------------------------------------------------------------------------

def pickup():
    motorZ.run_until_stalled(-400, then=Stop.HOLD, duty_limit=40)
    angleZ = motorZ.angle()
    
    adjustments = [
        (motorX, 0, motorY, -0.1),
        (motorX, -0.1, motorY, 0),
        (motorX, 0, motorY, 0.1),
        (motorX, 0, motorY, 0.1),
        (motorX, 0.1, motorY, 0),
        (motorX, 0.1, motorY, 0),
        (motorX, 0, motorY, -0.1),
        (motorX, 0, motorY, -0.1),
        (motorX, -0.1, motorY, 0.1)
    ]

    # adjustments = [
    #     (motorX, 0, motorY, 0.1),
    #     (motorX, 0.1, motorY, 0),
    #     (motorX, 0, motorY, -0.1),
    #     (motorX, 0, motorY, -0.1),
    #     (motorX, -0.1, motorY, 0),
    #     (motorX, -0.1, motorY, 0),
    #     (motorX, 0, motorY, 0.1),
    #     (motorX, 0, motorY, 0.1),
    #     (motorX, 0, motorY, 0.1),
    #     (motorX, 0.1, motorY, 0),
    #     (motorX, 0.1, motorY, 0),
    #     (motorX, 0.1, motorY, 0),
    #     (motorX, 0, motorY, -0.1),
    #     (motorX, 0, motorY, -0.1),
    #     (motorX, 0, motorY, -0.1),
    #     (motorX, 0, motorY, -0.1),
    #     (motorX, -0.1, motorY, 0),
    #     (motorX, -0.1, motorY, 0),
    #     (motorX, -0.1, motorY, 0),
    #     (motorX, -0.1, motorY, 0),
    #     (motorX, 0, motorY, 0.1),
    #     (motorX, 0, motorY, 0.1),
    #     (motorX, 0, motorY, 0.1),
    #     (motorX, 0, motorY, 0.1)
    # ]

    motorZ.run_target(400, 0)
    motorZ.stop()

    for adj in adjustments:
        motor1, angle1, motor2, angle2 = adj
        print(angleZ)

        if angleZ >= -190:
            motor1.run_angle(800, calculate_degree(angle1), then=Stop.HOLD)
            motor2.run_angle(800, calculate_degree(angle2), then=Stop.HOLD)

            motorZ.run_until_stalled(-400, then=Stop.HOLD, duty_limit=40)
            angleZ = motorZ.angle()
            motorZ.run_target(400, 0)
        else:
            break        

def place():

    if (ev3.battery.voltage() >= 7500):
        dl = 40
    else:
        dl = 50

    motorZ.run_until_stalled(-800, then=Stop.HOLD, duty_limit=dl)
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

    drive((31,31))
    place()

    drive((17,24))
    place()
    drive((14,19))
    place()
    drive((12,12))
    place()
    drive((5,10))
    place()

    drive((0,0))
    place()

    drive((6,28))
    place()

    drive((0,0))
    place()

    drive((20,33))
    pickup()
    drive((20,31))
    place()

    drive((22,33))
    pickup()
    drive((22,31))
    place()

    drive((24,33))
    pickup()
    drive((24,31))
    place()

    drive((26,33))
    pickup()
    drive((26,31))
    place()

    drive((0,0))
    pickup()

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
