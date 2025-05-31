#!/usr/bin/env pybricks-micropython

from pybricks.hubs import EV3Brick
from pybricks.parameters import Port, Direction, Stop, Button
from pybricks.ev3devices import Motor, TouchSensor
from pybricks.tools import wait
from pybricks.media.ev3dev import SoundFile

from pybricks.messaging import BluetoothMailboxServer, TextMailbox

import threading

#-------------------------------------------------------------------------

# adjustments = [
#         (self.motorX, 0, self.motorY, -0.1),
#         (self.motorX, -0.1, self.motorY, 0),
#         (self.motorX, 0, self.motorY, 0.1),
#         (self.motorX, 0, self.motorY, 0.1),
#         (self.motorX, 0.1, self.motorY, 0),
#         (self.motorX, 0.1, self.motorY, 0),
#         (self.motorX, 0, self.motorY, -0.1),
#         (self.motorX, 0, self.motorY, -0.1),
#         (self.motorX, -0.1, self.motorY, 0.1)
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
#         (self.motorX, 0, self.motorY, 0.1),
#         (self.motorX, 0.1, self.motorY, 0),
#         (self.motorX, 0, self.motorY, -0.1),
#         (self.motorX, 0, self.motorY, -0.1),
#         (self.motorX, -0.1, self.motorY, 0),
#         (self.motorX, -0.1, self.motorY, 0),
#         (self.motorX, 0, self.motorY, 0.1),
#         (self.motorX, 0, self.motorY, 0.1),
#         (self.motorX, 0, self.motorY, 0.1),
#         (self.motorX, 0.1, self.motorY, 0),
#         (self.motorX, 0.1, self.motorY, 0),
#         (self.motorX, 0.1, self.motorY, 0),
#         (self.motorX, 0, self.motorY, -0.1),
#         (self.motorX, 0, self.motorY, -0.1),
#         (self.motorX, 0, self.motorY, -0.1),
#         (self.motorX, 0, self.motorY, -0.1),
#         (self.motorX, -0.1, self.motorY, 0),
#         (self.motorX, -0.1, self.motorY, 0),
#         (self.motorX, -0.1, self.motorY, 0),
#         (self.motorX, -0.1, self.motorY, 0),
#         (self.motorX, 0, self.motorY, 0.1),
#         (self.motorX, 0, self.motorY, 0.1),
#         (self.motorX, 0, self.motorY, 0.1),
#         (self.motorX, 0, self.motorY, 0.1)
#     ]

class PixelArtRobot():
    def __init__(self):

        # Initialize the ev3.
        self.ev3 = EV3Brick()

        self.motorX = Motor(Port.B, positive_direction=Direction.COUNTERCLOCKWISE)
        self.motorY = Motor(Port.D, positive_direction=Direction.COUNTERCLOCKWISE)
        self.motorZ = Motor(Port.C, positive_direction=Direction.COUNTERCLOCKWISE)

        self.touchSensorY = TouchSensor(Port.S1)
        self.touchSensorX = TouchSensor(Port.S2)

        #-------------------------------------------------------------------------

        self.onePlate= 0.85
        self.gearDiameter = 1.73
        # self.gearPitchDiameter = 1.54

        # self.pullCorrection = {"x": -0.025, "y": -0.1} #old
        self.pullCorrection = {"x": 0, "y": -0.1} #working

        # self.pushCorrection = {"x": 0.15, "y": -0.01} #old
        self.pushCorrection = {"x": 0.1, "y": 0} #working

        self.motorSpeed = 200
        self.parallelAxis = False
        
        self.isCalibrated = False #first calibration

        self.isPaused = False
        self.refill = False

        self.currCords = (-1000, -1000)

        self.pickedup = False
        self.placed = False

    #-------------------------------------------------------------------------

    def calculate_degree(self, cord, type=None, currentDegree=0):
        distance_cm = self.onePlate * cord

        scope = 3.14159265359 * self.gearDiameter
        rotations = distance_cm / scope
        degree = rotations * 360
        
        if type != None:
            if currentDegree > degree and (self.currCords[0] if type == 'x' else self.currCords[1]) != cord:
                # print(type + " pull")
                degree = self.calculate_degree(cord+self.pullCorrection[type])

            if currentDegree < degree and (self.currCords[0] if type == 'x' else self.currCords[1]) != cord:
                # print(type + " push")
                degree = self.calculate_degree(cord+self.pushCorrection[type])

        
        return degree

    #calibration -------------------------------------------------------------

    def calibrate_motorXY(self, motor, sensor):
        motor.run(-100)
        while not sensor.pressed():
            pass
        motor.brake()

        motor.run_time(100, 500)
        motor.run(-50)
        while not sensor.pressed():
            pass
        motor.brake()

    def calibration(self):
        self.calibrate_motorXY(self.motorX, self.touchSensorX)
        self.calibrate_motorXY(self.motorY, self.touchSensorY)
        wait(1000)

        self.motorY.run_angle(50, self.calculate_degree(0.62), then=Stop.HOLD)
        self.motorX.run_angle(50, self.calculate_degree(0.15), then=Stop.HOLD)
        wait(1000)
        self.motorY.stop()
        self.motorX.stop()

        self.motorZ.run_until_stalled(500, then=Stop.HOLD, duty_limit=40)
        # self.motorZ.run_time(-500, 300)
        self.motorZ.run_time(-500, 550)
        wait(1000)
        self.motorZ.stop()

        self.motorX.reset_angle(0)
        self.motorY.reset_angle(0)
        self.motorZ.reset_angle(0)

        self.isCalibrated = True
        
    #-------------------------------------------------------------------------

    def drive(self, cords):
        if self.isPaused:
            return

        if self.currCords[1] != cords[1]:
            # self.motorX.run_target(speed=motorSpeed, target_angle=calculate_degree(30, "x", self.motorX.angle()), then=Stop.HOLD) # for driving stability

            if self.parallelAxis:
                self.motorY.run_target(speed=self.motorSpeed, target_angle=self.calculate_degree(cords[1], "y", self.motorY.angle()), then=Stop.HOLD, wait=False)
            else:
                self.motorY.run_target(speed=self.motorSpeed, target_angle=self.calculate_degree(cords[1], "y", self.motorY.angle()), then=Stop.HOLD)

        if self.currCords[0] != cords[0] and not self.isPaused:
            self.motorX.run_target(speed=self.motorSpeed, target_angle=self.calculate_degree(cords[0], "x", self.motorX.angle()), then=Stop.HOLD)


        while self.motorY.speed() != 0:
            wait(100)
        
        wait(1000)
        self.currCords = cords

    #-------------------------------------------------------------------------

    def pickup(self):    
        if self.isPaused:
            return

        self.motorZ.run_until_stalled(400, then=Stop.HOLD, duty_limit=40)
        self.pickedup = True
        # angleZ = self.motorZ.angle()

        self.motorZ.run_target(500, 0)
        self.motorZ.stop()

        # for adj in adjustments:
        #     motor1, angle1, motor2, angle2 = adj
        #     print(angleZ)

        #     if angleZ >= -190:
        #         motor1.run_angle(800, calculate_degree(angle1), then=Stop.HOLD)
        #         motor2.run_angle(800, calculate_degree(angle2), then=Stop.HOLD)

        #         self.motorZ.run_until_stalled(400, then=Stop.HOLD, duty_limit=40)
        #         angleZ = self.motorZ.angle()
        #         self.motorZ.run_target(400, 0)
        #     else:
        #         break        


    def place(self):
        if self.isPaused:
            return

        # if (self.ev3.battery.voltage() >= 7500):
        #     place_dl = 40
        # else:
        #     place_dl = 50

        place_dl = 60
        test_dl = 31

        # self.motorZ.run_until_stalled(50, then=Stop.HOLD, duty_limit=test_dl)
        # angleZ = self.motorZ.angle()
        # self.motorZ.run_target(200, 0)

        # print(angleZ)

        # if angleZ <= 90:
        #     print("ERROR")

        #     for adj in adjustments:
        #         angleX, angleY = adj
        #         print(angleZ)

        #         if angleZ <= 90:
        #             if angleX != 0:
        #                 self.motorX.run_angle(motorSpeed, calculate_degree(angleX, "x", self.motorX.angle()), then=Stop.HOLD)

        #             if angleY != 0:
        #                 self.motorY.run_angle(motorSpeed, calculate_degree(angleY, "y", self.motorY.angle()), then=Stop.HOLD)

        #             wait(1000)

        #             self.motorZ.run_until_stalled(50, then=Stop.HOLD, duty_limit=test_dl)
        #             angleZ = self.motorZ.angle()
        #             self.motorZ.run_target(200, 0)
        #         else:
        #             break

        #         print("--------------------")

        self.motorZ.run_until_stalled(400, then=Stop.HOLD, duty_limit=place_dl)
        self.placed = True
        self.motorZ.run_target(500, 0)
        wait(1000)
        self.motorZ.stop()           

    #-------------------------------------------------------------------------

    def run(self, lego):
        refillItemCount = {"black": 0, "dark_bluish_grey": 0, "light_bluish_grey": 0, "white": 0}
        colorCords = {
            "black": (20, 33),
            "dark_bluish_grey": (22, 33),
            "light_bluish_grey": (24, 33),
            "white": (26, 33)
        }
        recalibration = False

        while len(lego) != 0:

            if self.isPaused:
                if not self.placed:
                    lego.insert(0, [cord, color])
                self.placed = False
                recalibration = True
                self.ev3.screen.clear()
                self.ev3.screen.draw_text(10, 10, "Paused")
                if self.refill:
                    self.ev3.screen.draw_text(10, 40, "Refill all colours.")
                    self.mbox.send("recalibration")
                    self.calibration()
                    recalibration = False
                    self.mbox.send("recalibrated")

            while self.isPaused:
                wait(10)

            if recalibration:
                self.mbox.send("recalibration")
                self.calibration()
                recalibration = False
                self.mbox.send("recalibrated")
            
            cord, color = lego.pop(0)

            x, y = map(int, cord.split(","))
            self.ev3.screen.clear()
            self.ev3.screen.draw_text(10, 10, str((x, y)))
            self.ev3.screen.draw_text(10, 40, str(color).upper())

            if self.pickedup:
                self.pickedup = False
            else:
                self.drive(colorCords[color])
                self.pickup()
                refillItemCount[color] += 1

            self.drive((x, y))
            self.place()
            
            if self.placed:
                self.mbox.send(cord)
                self.mbox.send(color)

            if any(count >= 14 for count in refillItemCount.values()):
                self.isPaused = True
                self.refill = True
                self.mbox.send("refill")
                refillItemCount = {"black": 0, "dark_bluish_grey": 0, "light_bluish_grey": 0, "white": 0}

        self.drive((0,0))
        self.mbox.send("finished")
    
    #-------------------------------------------------------------------------

    def test(self):
        
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

    def pause(self):
        self.isPaused = True
        self.motorX.stop(Stop.BRAKE)
        self.motorY.stop(Stop.BRAKE)
        self.motorZ.stop(Stop.BRAKE)

        self.ev3.speaker.play_file(SoundFile.GENERAL_ALERT)

        if self.isCalibrated:
            self.motorZ.run_target(500, 0)

    def receiveMessages(self):
        while True:
            self.mbox.wait()
            msg = self.mbox.read()

            if msg == "pause":
                self.pause()
            elif msg == "resume":
                self.isPaused = False
                self.refill = False
            elif msg.startswith("speed"):
                _, value = msg.split(":")
                self.motorSpeed = 800*(int(value) * 0.01)
            elif msg.startswith("parallelAxis"):
                _, value = msg.split(":")
                self.parallelAxis = bool(value)

    def pauseButton(self):
        while True:
            if Button.CENTER in self.ev3.buttons.pressed():
                self.pause()
                self.mbox.send("pause")
            wait(10)

    #-------------------------------------------------------------------------

    def start(self):
        self.ev3.speaker.set_volume(10)
        self.ev3.speaker.beep(500)
        self.ev3.speaker.beep(700)
        self.ev3.speaker.beep(900)

        server = BluetoothMailboxServer()
        self.mbox = TextMailbox("pixel", server)

        server.wait_for_connection()

        self.mbox.wait()

        lego = self.mbox.read()
        lego = eval(lego)

        self.ev3.speaker.play_file(SoundFile.CONFIRM)
        self.mbox.send("received lego data")

        threading.Thread(target=self.pauseButton).start()
        self.calibration()

        self.ev3.speaker.play_file(SoundFile.READY)
        self.mbox.send("ready")

        self.mbox.wait()
        msg = self.mbox.read()
        if msg == "run":
            self.ev3.speaker.set_volume(100)
            threading.Thread(target=self.receiveMessages).start()
            self.run(lego)

if __name__ == "__main__":
    robot = PixelArtRobot()
    robot.start()