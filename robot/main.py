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
        self.pullCorrection = {"x": 0.1, "y": -0.1} #working x,y negative (31-0)

        # self.pushCorrection = {"x": 0.15, "y": -0.01} #old
        self.pushCorrection = {"x": 0.1, "y": 0} #working x,y positive (0-31)

        self.motorSpeed = 200
        self.parallelAxis = False
        
        self.isCalibrated = False #first calibration

        self.isPaused = False
        self.refill = False

        self.currCords = (-1000, -1000)

        self.pickedupAngle = 0
        self.placedAngle = 0

    #-------------------------------------------------------------------------

    def calculate_degree(self, cord, type=None, currentDegree=0):
        print("OK")
        distance_cm = self.onePlate * cord

        scope = 3.14159265359 * self.gearDiameter
        rotations = distance_cm / scope
        degree = rotations * 360

        if self.ev3.battery.voltage() > 7900:
            pullCorrection = {"x": 0.05, "y": -0.05} # x,y negative (31-0)
            pushCorrection = {"x": 0.05, "y": -0.05} # x,y positive (0-31)
        else:
            pullCorrection = {"x": 0.1, "y": -0.1}
            pushCorrection = {"x": 0.05, "y": 0}
        
        if type != None:
            if currentDegree > degree and (self.currCords[0] if type == 'x' else self.currCords[1]) != cord:
                degree = self.calculate_degree(cord+pullCorrection[type])

            if currentDegree < degree and (self.currCords[0] if type == 'x' else self.currCords[1]) != cord:
                degree = self.calculate_degree(cord+pushCorrection[type])
        
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
        # x, y calibration
        self.calibrate_motorXY(self.motorX, self.touchSensorX)
        self.calibrate_motorXY(self.motorY, self.touchSensorY)
        wait(1000)

        self.motorY.run_angle(50, self.calculate_degree(0.62), then=Stop.HOLD)
        self.motorX.run_angle(50, self.calculate_degree(0.15), then=Stop.HOLD)
        wait(1000)
        self.motorY.stop()
        self.motorX.stop()
        self.motorX.reset_angle(0)
        self.motorY.reset_angle(0)

        # z calibration
        if not self.isCalibrated:
            self.motorZ.run_until_stalled(500, then=Stop.HOLD, duty_limit=40)
            # self.motorZ.run_time(-500, 300)
            self.motorZ.run_time(-500, 550)
            wait(1000)
            self.motorZ.stop()
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
        if not self.isPaused:
            self.currCords = cords

    #-------------------------------------------------------------------------

    def pickup(self):    
        if self.isPaused:
            return
        
        self.motorZ.run_until_stalled(400, then=Stop.HOLD, duty_limit=60)

        self.pickedupAngle = self.motorZ.angle()

        self.motorZ.run_target(500, 0)
        self.motorZ.stop()

    def place(self):
        if self.isPaused:
            return

        self.motorZ.run_until_stalled(400, then=Stop.HOLD, duty_limit=60)

        self.placedAngle = self.motorZ.angle()

        self.motorZ.run_target(500, 0)
        wait(1000)
        self.motorZ.stop()           

    #-------------------------------------------------------------------------

    def run(self, lego):
        refillItemCount = {"black": 0, "dark_bluish_grey": 0, "light_bluish_grey": 0, "white": 0}
        colorCords = {
            "black": (20, 33.1),
            "dark_bluish_grey": (22, 33.1),
            "light_bluish_grey": (24, 33.1),
            "white": (26, 33.1)
        }
        recalibration = False
        placed = False
        pickedup = False
        placeAttempt = 0

        while len(lego) != 0:
            
            # Handle pause and refill
            if self.isPaused:
                if not placed:
                    lego.insert(0, [cord, color])
                recalibration = True
                self.ev3.screen.clear()
                self.ev3.screen.draw_text(10, 10, "Paused")
                if self.refill:
                    self.ev3.screen.draw_text(10, 40, "Refill all colours.")
                    self.comm_mbox.send("recalibration")
                    self.calibration()
                    recalibration = False
                    self.comm_mbox.send("recalibrated")
            while self.isPaused:
                wait(10)

            # Handle recalibration
            if recalibration:
                self.ev3.screen.clear()
                self.ev3.screen.draw_text(10, 10, "Recalibration...")
                self.comm_mbox.send("recalibration")
                self.calibration()
                recalibration = False
                self.comm_mbox.send("recalibrated")
            
            # Get stone
            cord, color = lego.pop(0)
            placed = False
            x, y = map(int, cord.split(","))
            self.ev3.screen.clear()
            self.ev3.screen.draw_text(10, 10, str((x, y)))
            self.ev3.screen.draw_text(10, 40, str(color).upper())

            # Pickup logic
            if not pickedup:
                self.drive(colorCords[color])
                self.pickup()
                refillItemCount[color] += 1

            if not self.isPaused:
                if 240 < self.pickedupAngle < 250: # Probably successfully picked up
                    print("Probably successfully picked up")
                    pickedup = True

                elif self.pickedupAngle < 220: # Picked up multiple stones
                    print("Picked up multiple stones")
                    self.pause()
                    pickedup = False
                    self.pixel_mbox.send(["multiple stones", cord, color])
                    lego.insert(0, [cord, color])

                elif self.pickedupAngle > 250: # No stone in storage location
                    print("No stone in storage location")
                    self.pause()
                    pickedup = False
                    self.pixel_mbox.send(["no stone", cord, color])
                    lego.insert(0, [cord, color])

            # Place logic
            self.drive((x, y))
            self.place()

            if not self.isPaused:
                if 190 < self.placedAngle < 200: # Successfully placed
                    print("Successfully placed")
                    placeAttempt = 0
                    pickedup = False
                    placed = True
                    self.pixel_mbox.send(["placed", cord, color])

                elif self.placedAngle > 220: # Not placed and not picked up
                    print("Not placed and not picked up")
                    pickedup = False
                    if placeAttempt >= 2:
                        placed = True
                        placeAttempt = 0
                        self.pixel_mbox.send(["couldnt placed", cord, color])
                    else:
                        placeAttempt += 1
                        lego.insert(0, [cord, color])

                elif self.placedAngle < 190: # Not placed but picked up
                    print("Not placed but picked up")

                    if placeAttempt >= 2:
                        pickedup = False
                        placed = True

                        placeAttempt = 0
                        self.pause()
                        self.pixel_mbox.send(["couldnt placed with stone", cord, color])
                    else:
                        placeAttempt += 1
                        pickedup = True
                        refillItemCount[color] -= 1
                        lego.insert(0, [cord, color])

            # Refill check
            if any(count >= 14 for count in refillItemCount.values()):
                self.isPaused = True
                self.refill = True
                self.comm_mbox.send("refill")
                refillItemCount = {"black": 0, "dark_bluish_grey": 0, "light_bluish_grey": 0, "white": 0}

        self.ev3.screen.clear()
        self.ev3.screen.draw_text(10, 10, "Finished!")
        self.pixel_mbox.send(["finished"])
        self.drive((0,0))
    
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
            self.comm_mbox.wait()
            msg = self.comm_mbox.read()

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
                self.comm_mbox.send("pause")
                self.pause()
            wait(10)

    #-------------------------------------------------------------------------

    def test(self):
        self.pickup()
        # self.calibration()

        # for x in range(32):
        #     self.drive((x,30))
        #     self.place()

        # self.drive((3,3))

    def start(self):
        # self.test()

        self.ev3.speaker.set_volume(10)
        self.ev3.speaker.beep(500)
        self.ev3.speaker.beep(700)
        self.ev3.speaker.beep(900)

        server = BluetoothMailboxServer()
        self.pixel_mbox = TextMailbox("pixel", server)
        self.comm_mbox = TextMailbox("comm", server)

        server.wait_for_connection()

        self.pixel_mbox.wait()

        lego = self.pixel_mbox.read()
        lego = eval(lego)

        self.ev3.speaker.play_file(SoundFile.CONFIRM)
        self.pixel_mbox.send("received lego data")

        threading.Thread(target=self.pauseButton).start()
        threading.Thread(target=self.receiveMessages).start()
        self.calibration()

        self.ev3.speaker.play_file(SoundFile.READY)
        self.pixel_mbox.send("ready")

        self.pixel_mbox.wait()
        msg = self.pixel_mbox.read()
        if msg == "run":
            self.ev3.speaker.set_volume(10)
            self.run(lego)

if __name__ == "__main__":
    robot = PixelArtRobot()
    robot.start()