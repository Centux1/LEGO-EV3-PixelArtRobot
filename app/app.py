from tkinter import scrolledtext
import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES

from PIL import Image
import os
import datetime
import time
import threading
import paramiko
import ast

from pybricks2.messaging import BluetoothMailboxClient, TextMailbox

from imgProcessing import convert_image

ctk.set_appearance_mode("dark")

class App(ctk.CTk, TkinterDnD.DnDWrapper):

    #GUI -----------------------------------------------------------------
    def __init__(self):
        super().__init__()

        # basic config
        self.title("PixelArtRobot")
        self.geometry(f"{800}x{530}")
        self.resizable(width=False, height=False)

        # when the window is closed
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        #-----------------------------------------------------------------

        imagePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "img")
        self.printImage = None
        self.needItemCount = {}
        self.placedItemCount = {"black": 0, "dark_bluish_grey": 0, "light_bluish_grey": 0, "white":0}
        self.refillItemCount = {"black": 0, "dark_bluish_grey": 0, "light_bluish_grey": 0, "white":0}
        self.lego = {}

        #-----------------------------------------------------------------

        self.arrowRight = ctk.CTkImage(
            light_image=Image.open(os.path.join(imagePath, "arrow_right.png")),
            dark_image=Image.open(os.path.join(imagePath, "arrow_right.png")), size=(64, 64))
        
        self.upload = ctk.CTkImage(
            light_image=Image.open(os.path.join(imagePath, "upload.png")),
            dark_image=Image.open(os.path.join(imagePath, "upload.png")), size=(64, 64))
        
        self.brush = ctk.CTkImage(
            light_image=Image.open(os.path.join(imagePath, "brush.png")),
            dark_image=Image.open(os.path.join(imagePath, "brush.png")), size=(64, 64))
        
        self.blackPlate = ctk.CTkImage(
            light_image=Image.open(os.path.join(imagePath, "black.png")),
            dark_image=Image.open(os.path.join(imagePath, "black.png")), size=(32, 32))
        
        self.darkPlate = ctk.CTkImage(
            light_image=Image.open(os.path.join(imagePath, "dark_bluish_grey.png")),
            dark_image=Image.open(os.path.join(imagePath, "dark_bluish_grey.png")), size=(32, 32))
        
        self.lightPlate = ctk.CTkImage(
            light_image=Image.open(os.path.join(imagePath, "light_bluish_grey.png")),
            dark_image=Image.open(os.path.join(imagePath, "light_bluish_grey.png")), size=(32, 32))
        
        self.whitePlate = ctk.CTkImage(
            light_image=Image.open(os.path.join(imagePath, "white.png")),
            dark_image=Image.open(os.path.join(imagePath, "white.png")), size=(32, 32))

        #-----------------------------------------------------------------

        self.show_frame(Page1)

    #Functions -----------------------------------------------------------

    def on_closing(self):
        try:
            self.destroy()
        except:
            pass

        #-----------------------------------------------------------------

    def show_frame(self, page):
        frame = page(master=self)
        frame.grid(row=0, column=0, sticky="nsew")

        frame.tkraise()

        #-----------------------------------------------------------------

#-------------------------------------------------------------------------

class Page1(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(corner_radius=0)

        self.TkdndVersion = TkinterDnD._require(self)
        self.master = master

        #-----------------------------------------------------------------

        self.imgPath = ""
        self.processedImg = None

        self.IMGSIZE = 320

        #-----------------------------------------------------------------

        self.imageFrame = ctk.CTkFrame(self)
        self.imageFrame.grid(column=0, row=0, columnspan=2, padx=(10, 10), pady=(10, 10), sticky="nsew")
        # self.imageFrame.grid_columnconfigure(0, weight=1)
        # self.imageFrame.grid_rowconfigure((0, 2), weight=1)

            #-------------------------------------------------------------

        self.selectImageFrame = ctk.CTkFrame(self.imageFrame, width=self.IMGSIZE, height=self.IMGSIZE, cursor="hand2")
        self.selectImageFrame.grid(column=0, row=0, padx=(10, 10), pady=(10, 10), sticky="w")
        self.selectImageFrame.columnconfigure(0, weight=1)
        self.selectImageFrame.rowconfigure(0, weight=1)
        self.selectImageFrame.grid_propagate(False)

        self.selectImageLabel = ctk.CTkLabel(self.selectImageFrame, 
                                             text="Choose a file or drag it here.", fg_color="transparent", font=("", 15), image=self.master.upload, compound="top")
        self.selectImageLabel.grid(column=0, row=0, padx=(0, 0), pady=(0, 0), sticky="nsew")
        self.selectImageLabel.drop_target_register(DND_FILES)
        self.selectImageLabel.dnd_bind("<<Drop>>", self.dnd)
        self.selectImageLabel.bind("<Button-1>", self.fileDialog)

            #-------------------------------------------------------------

        self.processedArrowRightLabel = ctk.CTkLabel(self.imageFrame, text="", image=self.master.arrowRight)
        self.processedArrowRightLabel.grid(column=1, row=0, padx=(0, 0), pady=(0, 0), sticky="nsew")

            #-------------------------------------------------------------

        self.processedImageFrame = ctk.CTkFrame(self.imageFrame, width=self.IMGSIZE, height=self.IMGSIZE)
        self.processedImageFrame.grid(column=2, row=0, padx=(10, 10), pady=(10, 10), sticky="e")
        self.processedImageFrame.columnconfigure(0, weight=1)
        self.processedImageFrame.rowconfigure(0, weight=1)
        self.processedImageFrame.grid_propagate(False)

        self.processedImageLabel = ctk.CTkLabel(self.processedImageFrame, text="", fg_color="transparent", image=self.master.brush)
        self.processedImageLabel.grid(column=0, row=0, padx=(0, 0), pady=(0, 0), sticky="nsew")
            
            #-------------------------------------------------------------

        self.processingButton = ctk.CTkButton(self.imageFrame, text="Processing", width=100, height=30,
                                                         fg_color="#696969", command=self.processing)
        self.processingButton.grid(column=1, row=1, padx=(0, 0), pady=(10, 10), sticky="nsew")

        #-----------------------------------------------------------------

        self.itemListFrame = ctk.CTkFrame(self)
        self.itemListFrame.grid(column=0, row=1, columnspan=2, padx=(10, 10), pady=(0, 10), sticky="nsew")
        self.itemListFrame.grid_columnconfigure((0, 3), weight=1)

            #-------------------------------------------------------------

        self.blackPlateFrame = ctk.CTkFrame(self.itemListFrame, height=50)
        self.blackPlateFrame.grid(column=0, row=0, padx=(10, 10), pady=(10, 10), sticky="e")
        self.blackPlateFrame.columnconfigure(1, weight=1)

        self.blackImgLabel = ctk.CTkLabel(self.blackPlateFrame, text="", fg_color="transparent", image=self.master.blackPlate)
        self.blackImgLabel.grid(column=0, row=0, padx=(10, 10), pady=(10, 10), sticky="w")

        self.blackTextLabel = ctk.CTkLabel(self.blackPlateFrame, text="0", fg_color="transparent")
        self.blackTextLabel.grid(column=1, row=0, padx=(10, 10), pady=(10, 10), sticky="e")

            #-------------------------------------------------------------

        self.darkPlateFrame = ctk.CTkFrame(self.itemListFrame, height=50)
        self.darkPlateFrame.grid(column=1, row=0, padx=(10, 10), pady=(10, 10), sticky="e")
        self.darkPlateFrame.columnconfigure(1, weight=1)

        self.darkImgLabel = ctk.CTkLabel(self.darkPlateFrame, text="", fg_color="transparent", image=self.master.darkPlate)
        self.darkImgLabel.grid(column=0, row=0, padx=(10, 10), pady=(10, 10), sticky="w")

        self.darkTextLabel = ctk.CTkLabel(self.darkPlateFrame, text="0", fg_color="transparent")
        self.darkTextLabel.grid(column=1, row=0, padx=(10, 10), pady=(10, 10), sticky="e")

            #-------------------------------------------------------------

        self.lightPlateFrame = ctk.CTkFrame(self.itemListFrame, height=50)
        self.lightPlateFrame.grid(column=2, row=0, padx=(10, 10), pady=(10, 10), sticky="w")
        self.lightPlateFrame.columnconfigure(1, weight=1)

        self.lightImgLabel = ctk.CTkLabel(self.lightPlateFrame, text="", fg_color="transparent", image=self.master.lightPlate)
        self.lightImgLabel.grid(column=0, row=0, padx=(10, 10), pady=(10, 10), sticky="w")

        self.lightTextLabel = ctk.CTkLabel(self.lightPlateFrame, text="0", fg_color="transparent")
        self.lightTextLabel.grid(column=1, row=0, padx=(10, 10), pady=(10, 10), sticky="e")

            #-------------------------------------------------------------

        self.whitePlateFrame = ctk.CTkFrame(self.itemListFrame, height=50)
        self.whitePlateFrame.grid(column=3, row=0, padx=(10, 10), pady=(10, 10), sticky="w")
        # self.whitePlateFrame.pack(side="left", expand=True)
        self.whitePlateFrame.columnconfigure(1, weight=1)

        self.whiteImgLabel = ctk.CTkLabel(self.whitePlateFrame, text="", fg_color="transparent", image=self.master.whitePlate)
        self.whiteImgLabel.grid(column=0, row=0, padx=(10, 10), pady=(10, 10), sticky="w")

        self.whiteTextLabel = ctk.CTkLabel(self.whitePlateFrame, text="0", fg_color="transparent")
        self.whiteTextLabel.grid(column=1, row=0, padx=(10, 10), pady=(10, 10), sticky="e")

        #-----------------------------------------------------------------

        self.startButton = ctk.CTkButton(
            self, text="Start", width=100, height=30, fg_color="#696969", command=self.start)
        self.startButton.grid(column=1, row=2, padx=(0, 120), pady=(0, 10), sticky="se")

        self.exitButton = ctk.CTkButton(
            self, text="Cancel", width=100, height=30, fg_color="#696969", command=self.on_closing)
        self.exitButton.grid(column=1, row=2, padx=(0, 10), pady=(0, 10), sticky="se")

    #Functions -----------------------------------------------------------

    def start(self):
        self.master.show_frame(Page2)

    def on_closing(self):
        try:
            self.master.destroy()
        except:
            pass

        #-----------------------------------------------------------------

    def dnd(self, event):
        self.showImage(event.data)
        self.imgPath = event.data

    def fileDialog(self, event):
        try:
            path = ctk.filedialog.askopenfilename()
            self.showImage(path)
            self.imgPath = path
        except Exception: 
            pass

    def showImage(self, path):
        image = Image.open(path)
        image = image.resize((self.IMGSIZE, self.IMGSIZE), Image.NEAREST)
        selecedImage = ctk.CTkImage(light_image=image, dark_image=image, size=(self.IMGSIZE, self.IMGSIZE))

        self.selectImageLabel.configure(text="", image=selecedImage)

        #-----------------------------------------------------------------

    def processing(self):
        if self.imgPath == "":
            return
        try:
            processedImg, lego, needItemCount = convert_image(self.imgPath)
        except Exception:
            pass
        
        self.master.lego = lego
        self.master.printImage = processedImg
        self.master.needItemCount = needItemCount

        processedImg = processedImg.resize((self.IMGSIZE, self.IMGSIZE), Image.NEAREST)
        processedCTkImg = ctk.CTkImage(light_image=processedImg, dark_image=processedImg, size=(self.IMGSIZE, self.IMGSIZE))

        self.processedImageLabel.configure(text="", image=processedCTkImg)

        self.blackTextLabel.configure(text=needItemCount["black"])
        self.darkTextLabel.configure(text=needItemCount["dark_bluish_grey"])
        self.lightTextLabel.configure(text=needItemCount["light_bluish_grey"])
        self.whiteTextLabel.configure(text=needItemCount["white"])

#-------------------------------------------------------------------------

class Page2(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)
        self.configure(corner_radius=0)

        self.master = master

        #-----------------------------------------------------------------

        self.printingImage = Image.new('RGBA', (32, 32), (0, 0, 0, 0))
        self.progressAnimationValue = 0
        self.remainingPrintingTime = None

        self.isStarting = False
        self.isPaused = False
        
        #-----------------------------------------------------------------

        self.inProgressFrame = ctk.CTkFrame(self)
        self.inProgressFrame.grid(column=0, row=0, padx=(10, 10), pady=(10, 10), sticky="nsew")
        # self.inProgressFrame.grid_propagate(False)

            #-------------------------------------------------------------

        self.printImageFrame = ctk.CTkFrame(self.inProgressFrame, width=160, height=160)
        self.printImageFrame.grid(column=0, row=0, padx=(10, 10), pady=(10, 10), sticky="w")
        self.printImageFrame.columnconfigure(0, weight=1)
        self.printImageFrame.rowconfigure(0, weight=1)
        self.printImageFrame.grid_propagate(False)

        self.printImageLabel = ctk.CTkLabel(self.printImageFrame, text="")
        self.printImageLabel.grid(column=0, row=0, padx=(0, 0), pady=(0, 0), sticky="nsew")

            #-------------------------------------------------------------

        self.progressAnimationBar = ctk.CTkProgressBar(self.inProgressFrame, width=90)
        self.progressAnimationBar.grid(column=1, row=0, padx=(0, 0), pady=(0, 0), sticky="ew")
        self.progressAnimationBar.set(0)

            #-------------------------------------------------------------

        self.printFrame = ctk.CTkFrame(self.inProgressFrame, width=320, height=320)
        # self.printFrame.grid(column=2, row=0, padx=(10, 10), pady=(35, 35), sticky="e")
        self.printFrame.grid(column=2, row=0, padx=(10, 10), pady=(10, 10), sticky="e")
        self.printFrame.columnconfigure(0, weight=1)
        self.printFrame.rowconfigure(0, weight=1)
        self.printFrame.grid_propagate(False)

        self.printLabel = ctk.CTkLabel(self.printFrame, text="")
        self.printLabel.grid(column=0, row=0, padx=(0, 0), pady=(0, 0), sticky="nsew")
            
        #-----------------------------------------------------------------

        self.itemListFrame = ctk.CTkFrame(self)
        self.itemListFrame.grid(column=1, row=0, rowspan=2, padx=(0, 10), pady=(10, 10), sticky="nsew")
        self.itemListFrame.grid_rowconfigure((0, 3), weight=1)

            #-------------------------------------------------------------

        self.blackPlateFrame = ctk.CTkFrame(self.itemListFrame)
        self.blackPlateFrame.grid(column=0, row=0, padx=(10, 10), pady=(10, 10), sticky="s")
        self.blackPlateFrame.columnconfigure(1, weight=1)

        self.blackImgLabel = ctk.CTkLabel(self.blackPlateFrame, text="", fg_color="transparent", image=self.master.blackPlate)
        self.blackImgLabel.grid(column=0, row=0, padx=(10, 10), pady=(10, 10), sticky="w")

        self.blackTextLabel = ctk.CTkLabel(self.blackPlateFrame, text="0/0", fg_color="transparent", width=70)
        self.blackTextLabel.grid(column=1, row=0, padx=(10, 10), pady=(10, 10), sticky="e")

            #-------------------------------------------------------------

        self.darkPlateFrame = ctk.CTkFrame(self.itemListFrame)
        self.darkPlateFrame.grid(column=0, row=1, padx=(10, 10), pady=(0, 10), sticky="s")
        self.darkPlateFrame.columnconfigure(1, weight=1)

        self.darkImgLabel = ctk.CTkLabel(self.darkPlateFrame, text="", fg_color="transparent", image=self.master.darkPlate)
        self.darkImgLabel.grid(column=0, row=0, padx=(10, 10), pady=(10, 10), sticky="w")

        self.darkTextLabel = ctk.CTkLabel(self.darkPlateFrame, text="0/0", fg_color="transparent", width=70)
        self.darkTextLabel.grid(column=1, row=0, padx=(10, 10), pady=(10, 10), sticky="e")

            #-------------------------------------------------------------

        self.lightPlateFrame = ctk.CTkFrame(self.itemListFrame)
        self.lightPlateFrame.grid(column=0, row=2, padx=(10, 10), pady=(0, 10), sticky="n")
        self.lightPlateFrame.columnconfigure(1, weight=1)

        self.lightImgLabel = ctk.CTkLabel(self.lightPlateFrame, text="", fg_color="transparent", image=self.master.lightPlate)
        self.lightImgLabel.grid(column=0, row=0, padx=(10, 10), pady=(10, 10), sticky="w")

        self.lightTextLabel = ctk.CTkLabel(self.lightPlateFrame, text="0/0", fg_color="transparent", width=70)
        self.lightTextLabel.grid(column=1, row=0, padx=(10, 10), pady=(10, 10), sticky="e")

            #-------------------------------------------------------------

        self.whitePlateFrame = ctk.CTkFrame(self.itemListFrame)
        self.whitePlateFrame.grid(column=0, row=3, padx=(10, 10), pady=(0, 10), sticky="n")
        self.whitePlateFrame.columnconfigure(1, weight=1)

        self.whiteImgLabel = ctk.CTkLabel(self.whitePlateFrame, text="", fg_color="transparent", image=self.master.whitePlate)
        self.whiteImgLabel.grid(column=0, row=0, padx=(10, 10), pady=(10, 10), sticky="w")

        self.whiteTextLabel = ctk.CTkLabel(self.whitePlateFrame, text="0/0", fg_color="transparent", width=70)
        self.whiteTextLabel.grid(column=1, row=0, padx=(10, 10), pady=(10, 10), sticky="e")

        #-----------------------------------------------------------------

        self.progressFrame = ctk.CTkFrame(self)
        self.progressFrame.grid(column=0, row=1, padx=(10, 10), pady=(0, 10), sticky="nsew")
        self.progressFrame.grid_columnconfigure((0, 2), weight=1)
        # self.progressFrame.grid_propagate(False)

            #-------------------------------------------------------------

        self.progressBar = ctk.CTkProgressBar(self.progressFrame, width=250, height=10)
        self.progressBar.grid(column=0, row=0, padx=(0, 10), pady=(10, 10), sticky="e")
        self.progressBar.set(0)

        self.progressPercentageLabel = ctk.CTkLabel(self.progressFrame, text="0%")
        self.progressPercentageLabel.grid(column=1, row=0, padx=(0, 0), pady=(10, 10), sticky="e")

        self.progressRemainingTimeLabel = ctk.CTkLabel(self.progressFrame, text="    -    Calculating...")
        self.progressRemainingTimeLabel.grid(column=2, row=0, padx=(0, 0), pady=(10, 10), sticky="w")

        #-----------------------------------------------------------------

        self.infoFrame = ctk.CTkFrame(self)
        self.infoFrame.grid(column=0, row=2, columnspan= 2, padx=(10, 10), pady=(0, 10), sticky="nsew")
        # self.infoFrame.grid_propagate(False)

            #-------------------------------------------------------------

        self.infoTextBox = ctk.CTkTextbox(self.infoFrame, height=53, width=760, fg_color="transparent")
        self.infoTextBox.grid(column=0, row=0, padx=(10, 10), pady=(5, 5), sticky="nsew")

        self.infoTextBox.insert("end", "---- EV3 LEGO PIXEL-ART ROBOT ----" )
        self.infoTextBox.configure(state="disabled")

        #-----------------------------------------------------------------

        self.manageButton = ctk.CTkButton(
            self, text="Pause", width=100, height=30, fg_color="#696969", command=self.pause)
        self.manageButton.grid(column=0, row=3, columnspan=2, padx=(0, 120), pady=(0, 10), sticky="ne")

        self.exitButton = ctk.CTkButton(
            self, text="Cancel", width=100, height=30, fg_color="#696969", command=self.on_closing)
        self.exitButton.grid(column=0, row=3, columnspan=2, padx=(0, 10), pady=(0, 10), sticky="ne")

        #-----------------------------------------------------------------

        threading.Thread(target=self.onStarting).start()

    #Functions -----------------------------------------------------------

    def on_closing(self):
        try:
            self.master.destroy()
            self.ssh.exec_command("exit")
        except:
            pass

    def pause(self):
        self.isPaused = True
        self.insertInfoTextBox("warning", "Printing has been paused.")
        self.mbox.send("pause")
        self.manageButton.configure(text="Continue", text_color="#ff8800", command=self.resume)

    def refill(self):
        self.isPaused = True
        self.insertInfoTextBox("warning", "Please refill all colours.")
        self.mbox.send("refill")
        self.manageButton.configure(text="Continue", text_color="#ff8800", command=self.resume)

    def resume(self):
        self.isPaused = False
        self.insertInfoTextBox("warning", "Printing has been continued.")
        self.mbox.send("resume")
        self.manageButton.configure(text="Pause", text_color="#ffffff", command=self.pause)

    def startError(self):
        self.isStarting = False
        self.manageButton.configure(text="Retry", text_color="#ff8800", command=lambda: threading.Thread(target=self.onStarting).start())

    def resetManageButton(self):
        self.manageButton.configure(text="Pause", text_color="#ffffff", command=self.pause)

        #-----------------------------------------------------------------
    
    def onStarting(self):
        if self.isStarting == True:
            return
        
        self.isStarting = True

        #update content
        self.updateContent()

        #start mindstorms
        ev3Start = self.startMindstorms()
        if ev3Start == False:
            self.startError()
            return

        #connect to mindstorms 
        SERVER = "F4:84:4C:CA:82:23"

        client = BluetoothMailboxClient()

        self.mbox = TextMailbox("pixel", client)
        
        time.sleep(1)
        self.insertInfoTextBox("msg", "Connection to EV3 Mailbox is attempted...")
        try:
            client.connect(SERVER)
        except Exception as e:
            self.insertInfoTextBox("error", "The EV3 Mailbox Server is not available.")
            self.startError()
            return
        self.insertInfoTextBox("msg", "Connection to EV3 Mailbox has been established.")

        time.sleep(1)

        self.insertInfoTextBox("msg", "Sending printing data to EV3...")
        self.mbox.send(self.master.lego)

        self.mbox.wait()
        msg = self.mbox.read()
        if msg == "received lego data":
            self.insertInfoTextBox("msg", "Printing data was sent successfully.")

            self.insertInfoTextBox("msg", "Calibration of the EV3 has started...")

            self.mbox.wait() 
            msg = self.mbox.read()
            if msg == "ready":
                self.insertInfoTextBox("msg", "Calibration of the EV3 is complete.")

                time.sleep(1)

                self.mbox.send("run")
                self.insertInfoTextBox("msg", "Printing has started...")

                self.resetManageButton()
                self.startTime = time.time()
                self.progressAnimation()
                self.timeAnimation()
                self.printingDataProcessing()

        else:
            self.insertInfoTextBox("error", "Printing data could not be transferred.")
            self.startError()

    def startMindstorms(self):
        self.ssh = paramiko.SSHClient()        
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.insertInfoTextBox("msg", "Connection to EV3 is attempted...")
        try:
            self.ssh.connect("ev3dev", username="robot", password="maker")
            self.insertInfoTextBox("msg", "Connection to EV3 has been established.")
        except Exception as e:
            self.insertInfoTextBox("error", "No connection with EV3 possible.")
            return False
        
        time.sleep(1)
        
        self.insertInfoTextBox("msg", "Programme is started on EV3...")
        brickrun_command = f'brickrun -r --directory="/home/robot/PixelArtRobot/robot" "/home/robot/PixelArtRobot/robot/main.py"'
        self.ssh.exec_command(brickrun_command)

        time.sleep(5)
        self.insertInfoTextBox("msg", "Programme has started successfully.")

        #-----------------------------------------------------------------

    def updateContent(self):
        image = self.master.printImage
        image = image.resize((160,160), Image.NEAREST)

        CTkImg = ctk.CTkImage(light_image=image, dark_image=image, size=(160, 160))
        self.printImageLabel.configure(image=CTkImg)

        self.updateItemCount()

    def updateItemCount(self):
        self.blackTextLabel.configure(text=str(self.master.placedItemCount["black"]) + "/" + str(self.master.needItemCount["black"]))
        self.darkTextLabel.configure(text=str(self.master.placedItemCount["dark_bluish_grey"]) + "/" + str(self.master.needItemCount["dark_bluish_grey"]))
        self.lightTextLabel.configure(text=str(self.master.placedItemCount["light_bluish_grey"]) + "/" + str(self.master.needItemCount["light_bluish_grey"]))
        self.whiteTextLabel.configure(text=str(self.master.placedItemCount["white"]) + "/" + str(self.master.needItemCount["white"]))

        #-----------------------------------------------------------------

    def printingDataProcessing(self):
        colorList = {
            "black": (5, 19, 29),
            "dark_bluish_grey": (108, 110, 104),
            "light_bluish_grey": (160, 165, 169),
            "white": (255, 255, 255)
        }

            #-------------------------------------------------------------

        self.mbox.wait()
        cord = self.mbox.read()

            #- Finished --------------------------------------------------

        if cord == "finished":
            self.isPaused = True
            self.progressAnimationBar.set(1)
            hours, remainder = divmod((time.time() - self.startTime), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.progressRemainingTimeLabel.configure(text=f"    -    Finished after {int(hours)} hours, {int(minutes)} minutes and {seconds:.0f} seconds.")
            return

            #-------------------------------------------------------------

        self.mbox.wait()
        color = self.mbox.read()
        cord = ast.literal_eval(cord)
        cord = (int(cord[0]), 31-int(cord[1]))

            #- PrintImage -----------------------------------------------

        self.printingImage.putpixel(cord, colorList[color])
        image = self.printingImage.resize((320,320), Image.NEAREST)
        printingCTkImg = ctk.CTkImage(light_image=image, dark_image=image, size=(320, 320))
        self.printLabel.configure(image=printingCTkImg)

            #- ItemCount/Process ----------------------------------------

        self.master.placedItemCount[color] += 1
        self.master.refillItemCount[color] += 1
        self.updateItemCount()

        totalNeedCount = 0
        for _, count in self.master.needItemCount.items():
            totalNeedCount += count

        totalPlacedCount = 0
        for _, count in self.master.placedItemCount.items():
            totalPlacedCount += count

        processPercentage = totalPlacedCount / totalNeedCount

        self.progressBar.set(processPercentage)
        self.progressPercentageLabel.configure(text=f"{processPercentage*100:.0f}%")

            #- Remaining Time --------------------------------------------

        betweenTime = time.time() - self.startTime

        timeOnePart = betweenTime / totalPlacedCount

        self.remainingPrintingTime = (totalNeedCount - totalPlacedCount) * timeOnePart

            #- Refill ----------------------------------------------------

        for _, count in self.master.refillItemCount.items():
            if count % 13 == 0 and count != 0:
                self.refill()
                self.master.refillItemCount = {"black": 0, "dark_bluish_grey": 0, "light_bluish_grey": 0, "white":0}
                break

            #- Restart ---------------------------------------------------

        self.printingDataProcessing()

        #-----------------------------------------------------------------

    def timeAnimation(self):
        if self.remainingPrintingTime != None and self.isPaused == False:
            self.remainingPrintingTime -= 1

            hours, remainder = divmod(self.remainingPrintingTime, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.progressRemainingTimeLabel.configure(text=f"    -    {int(hours)} hours, {int(minutes)} minutes and {seconds:.0f} seconds remaining.")

        self.after(1000, self.timeAnimation)

    def progressAnimation(self):
        if self.isPaused == False:
            self.progressAnimationValue += 0.01
            
            if self.progressAnimationValue >= 1:
                self.progressAnimationValue = 0
            
            self.progressAnimationBar.set(self.progressAnimationValue)
        
        self.after(6, self.progressAnimation)

        #-----------------------------------------------------------------

    def insertInfoTextBox(self, type, text):
        self.infoTextBox.configure(state="normal")
        time = datetime.datetime.now()
        time = time.strftime("%H:%M:%S")

        if type == "msg":
            self.infoTextBox.insert("end", f"\n[{time}] " + text)
        elif type == "warning":
            self.infoTextBox.insert("end", f"\n[{time}] [Warning] " + text)
        elif type == "error":
            self.infoTextBox.insert("end", f"\n[{time}] [ERROR] " + text)

        self.infoTextBox.see("end")
        self.infoTextBox.configure(state="disabled")
        
#-------------------------------------------------------------------------

if __name__ == "__main__":
    app = App()

    app.mainloop()


