import customtkinter as ctk
from tkinterdnd2 import TkinterDnD, DND_FILES

from PIL import Image
import os
import datetime
import time
import threading
import paramiko
import ctypes

from pybricksPC.messaging import BluetoothMailboxClient, TextMailbox

from imgProcessing import convert_image

EV3_HOST = "ev3dev"
EV3_USER = "robot"
EV3_PASS = "maker"
EV3_MAILBOX_SERVER = "F4:84:4C:CA:82:23"
EV3_MAIN_PATH = "/home/robot/PixelArtRobot/robot/main.py"
EV3_MAIN_DIR = "/home/robot/PixelArtRobot/robot"
COLOR_LIST = {
    "black": (5, 19, 29),
    "dark_bluish_grey": (108, 110, 104),
    "light_bluish_grey": (160, 165, 169),
    "white": (255, 255, 255)
}
IMGSIZE = 320

ctk.set_appearance_mode("dark")

class App(ctk.CTk, TkinterDnD.DnDWrapper):

    #GUI -----------------------------------------------------------------
    def __init__(self):
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        
        #-----------------------------------------------------------------

        super().__init__()
        self.title("EV3 - PixelArtRobot")
        self.geometry(f"{800}x{530}")
        self.resizable(width=False, height=False)
        self.protocol("WM_DELETE_WINDOW", self.close)

        #-----------------------------------------------------------------

        dpi_factor = self.winfo_fpixels('1i') / 144
        ctk.set_widget_scaling(dpi_factor)          
        ctk.set_window_scaling(dpi_factor)  
        
        #-----------------------------------------------------------------
        
        self.printImage = None
        self.needItemCount = {}
        self.placedItemCount = {"black": 0, "dark_bluish_grey": 0, "light_bluish_grey": 0, "white":0}
        self.lego = {}
        self.ssh = None

        #-----------------------------------------------------------------

        self._loadImages()
        self.show_frame(Page1)

    #---------------------------------------------------------------------

    def _loadImages(self):
        imagePath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "img")
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

    #---------------------------------------------------------------------

    def close(self):
        try:
            if self.ssh != None:
                self.ssh.exec_command("pkill -f main.py")
                self.ssh.exec_command("exit")
            self.destroy()
        except:
            pass

    #---------------------------------------------------------------------

    def show_frame(self, page):
        frame = page(master=self)
        frame.grid(row=0, column=0, sticky="nsew")

        frame.tkraise()

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

        #-----------------------------------------------------------------

        self._setup_ui()

    def _setup_ui(self):

        self.imageFrame = ctk.CTkFrame(self)
        self.imageFrame.grid(column=0, row=0, columnspan=2, padx=(10, 10), pady=(10, 10), sticky="nsew")
        # self.imageFrame.grid_columnconfigure(0, weight=1)
        # self.imageFrame.grid_rowconfigure((0, 2), weight=1)

            #-------------------------------------------------------------

        self.selectImageFrame = ctk.CTkFrame(self.imageFrame, width=IMGSIZE, height=IMGSIZE, cursor="hand2")
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

        self.processedImageFrame = ctk.CTkFrame(self.imageFrame, width=IMGSIZE, height=IMGSIZE)
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
            self, text="Confirm", width=100, height=30, fg_color="#696969", command=self.start)
        self.startButton.grid(column=1, row=2, padx=(0, 120), pady=(0, 10), sticky="se")

        self.exitButton = ctk.CTkButton(
            self, text="Cancel", width=100, height=30, fg_color="#696969", command=self.on_closing)
        self.exitButton.grid(column=1, row=2, padx=(0, 10), pady=(0, 10), sticky="se")

    #---------------------------------------------------------------------

    def start(self):
        if self.master.printImage == None:
            return

        self.master.show_frame(Page2)

    def on_closing(self):
        self.master.close()

    #---------------------------------------------------------------------

    def dnd(self, event): # drag and drop
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
        image = image.resize((IMGSIZE, IMGSIZE), Image.NEAREST)
        selecedImage = ctk.CTkImage(light_image=image, dark_image=image, size=(IMGSIZE, IMGSIZE))

        self.selectImageLabel.configure(text="", image=selecedImage)

    #---------------------------------------------------------------------

    def processing(self):
        if self.imgPath == "":
            return
        try:
            processedImg, lego, needItemCount = convert_image(self.imgPath)
        except Exception:
            return
        
        self.master.lego = lego
        self.master.printImage = processedImg
        self.master.needItemCount = needItemCount

        processedImg = processedImg.resize((IMGSIZE, IMGSIZE), Image.NEAREST)
        processedCTkImg = ctk.CTkImage(light_image=processedImg, dark_image=processedImg, size=(IMGSIZE, IMGSIZE))

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

        self.started = False
        self.isPaused = False

        self.pixel_mbox = None
        self.comm_mbox = None
        
        #-----------------------------------------------------------------

        self._setup_ui()
        threading.Thread(target=self.startup, daemon=True).start() # without threading page2 is never opened (stuck until func startup ends)

    def _setup_ui(self):

        self.inProgressFrame = ctk.CTkFrame(self)
        self.inProgressFrame.grid(column=0, row=0, rowspan=2, padx=(10, 10), pady=(10, 10), sticky="nsew")

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
        self.itemListFrame.grid(column=1, row=0, padx=(0, 10), pady=(10, 10), sticky="nsew")
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

        self.settingsFrame = ctk.CTkFrame(self)
        self.settingsFrame.grid(column=1, row=1, rowspan=2, padx=(0, 10), pady=(0, 10), sticky="nsew")
        self.settingsFrame.grid_rowconfigure((0, 1), weight=1)
        self.settingsFrame.grid_columnconfigure((0, 1), weight=1)

            #-------------------------------------------------------------

        self.speedLabel = ctk.CTkLabel(self.settingsFrame, text="Speed (%)")
        self.speedLabel.grid(column=0, row=0, padx=(0, 20), pady=(0, 10), sticky="se")

        self.speedVar = ctk.StringVar(value="25")
        self.speedVar.trace_add("write", self.speedVarChange)
        self.speedEntry = ctk.CTkEntry(self.settingsFrame, textvariable=self.speedVar, width=40, state="disabled")
        self.speedEntry.grid(column=1, row=0, padx=(0, 0), pady=(0, 10), sticky="sw")

            #-------------------------------------------------------------

        self.parallelAxisLabel = ctk.CTkLabel(self.settingsFrame, text="Simul. axis")
        self.parallelAxisLabel.grid(column=0, row=1, padx=(0, 20), pady=(0, 0), sticky="ne")

        self.parallelAxisVar = ctk.BooleanVar(value=False)
        self.parallelAxisVar.trace_add("write", self.parallelAxisVarChange)
        self.parallelAxisCheckbox = ctk.CTkCheckBox (
            self.settingsFrame,
            text=None,
            variable=self.parallelAxisVar,
            onvalue=True,
            offvalue=False,
            width=24,
            state="disabled"
        )
        self.parallelAxisCheckbox.grid(column=1, row=1, padx=(0, 0), pady=(0, 0), sticky="nw")

        #-----------------------------------------------------------------

        self.progressFrame = ctk.CTkFrame(self)
        self.progressFrame.grid(column=0, row=2, padx=(10, 10), pady=(0, 10), sticky="nsew")
        self.progressFrame.grid_columnconfigure((0, 2), weight=1)

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
        self.infoFrame.grid(column=0, row=3, columnspan=2, padx=(10, 10), pady=(0, 10), sticky="nsew")

            #-------------------------------------------------------------

        self.infoTextBox = ctk.CTkTextbox(self.infoFrame, height=53, width=760, fg_color="transparent")
        self.infoTextBox.grid(column=0, row=0, padx=(10, 10), pady=(5, 5), sticky="nsew")

        self.infoTextBox.insert("end", "---- EV3 LEGO PIXEL-ART ROBOT ----" )
        self.infoTextBox.configure(state="disabled")

        #-----------------------------------------------------------------

        self.manageButton = ctk.CTkButton(
            self, text="Start", width=100, height=30, fg_color="#696969", command=self.startPrinting, state="disabled")
        self.manageButton.grid(column=0, row=4, columnspan=2, padx=(0, 120), pady=(0, 10), sticky="ne")

        self.exitButton = ctk.CTkButton(
            self, text="Cancel", width=100, height=30, fg_color="#696969", command=self.on_closing)
        self.exitButton.grid(column=0, row=4, columnspan=2, padx=(0, 10), pady=(0, 10), sticky="ne")

    #---------------------------------------------------------------------

    def on_closing(self):
        self.master.close()

    def pause(self, ev3=False):
        self.isPaused = True
        self.insertInfoTextBox("warning", "Printing has been paused.")
        if not ev3:
            self.comm_mbox.send("pause")
        self.manageButton.configure(text="Continue", text_color="#ff8800", command=self.resume)

    def refill(self):
        self.isPaused = True
        self.insertInfoTextBox("warning", "Printing has been paused.")
        self.insertInfoTextBox("warning", "Please refill all colours.")
        self.manageButton.configure(text="Continue", text_color="#ff8800", command=self.resume, state="disabled")

    def resume(self):
        self.isPaused = False
        self.insertInfoTextBox("warning", "Printing has been continued.")
        self.comm_mbox.send("resume")
        self.resetManageButton()
  
    def recalibration(self):
        self.insertInfoTextBox("msg", "Recalibration of the EV3 has started...")

    def startError(self):
        self.started = False
        self.manageButton.configure(text="Retry", text_color="#ff8800", command=lambda: threading.Thread(target=self.startup).start(), state="normal")

    def resetManageButton(self):
        self.manageButton.configure(text="Pause", text_color="#ffffff", command=self.pause)

    #---------------------------------------------------------------------
    
    def startup(self):
        if self.started:
            return
        self.started = True

        self.manageButton.configure(text="Start", fg_color="#696969", command=self.startPrinting, state="disabled") #update manage button
        self.updateContent() #update content on page2

        #starts the programm on the EV3
        ev3Start = self.startProgramm()
        if not ev3Start:
            self.insertInfoTextBox("error", "No connection with EV3 possible.")
            self.startError()
            return
        
        #connect to mailbox
        mailboxStart = self.startMailbox()
        if not mailboxStart:
            # self.insertInfoTextBox("error", "The EV3 or the EV3 Mailbox Server is not available.")
            self.insertInfoTextBox("error", "The EV3 Mailbox Server is not available.")
            self.startError()
            return

        #send printing data to ev3
        self.insertInfoTextBox("msg", "Sending printing data to EV3...")
        self.pixel_mbox.send(self.master.lego)

        self.pixel_mbox.wait()
        msg = self.pixel_mbox.read()

        if msg != "received lego data":
            self.insertInfoTextBox("error", "Printing data could not be transferred.")
            self.startError()
            return 

        self.insertInfoTextBox("msg", "Printing data was sent successfully.")

        #enable settings
        self.speedEntry.configure(state="normal")
        self.parallelAxisCheckbox.configure(state="normal")

        #calibration
        self.insertInfoTextBox("msg", "Calibration of the EV3 has started...")

        self.pixel_mbox.wait() 
        msg = self.pixel_mbox.read()

        #ready for printing
        if msg == "ready":
            self.insertInfoTextBox("msg", "Calibration of the EV3 is complete.")

            time.sleep(1)
            self.insertInfoTextBox("msg", "Press Start to initiate the printing process.")
            self.manageButton.configure(state="normal")

    def startProgramm(self):
        self.master.ssh = paramiko.SSHClient()        
        self.master.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.insertInfoTextBox("msg", "Connection to EV3 is attempted...")
        try:
            self.master.ssh.connect(hostname=EV3_HOST, username=EV3_USER,password=EV3_PASS,look_for_keys=False,allow_agent=False)
            self.insertInfoTextBox("msg", "Connection to EV3 has been established.")
        except Exception:
            return False
        
        time.sleep(1)
        self.insertInfoTextBox("msg", "Programme is started on EV3...")
        brickrun_command = f'brickrun -r --directory="{EV3_MAIN_DIR}" "{EV3_MAIN_PATH}"'
        self.master.ssh.exec_command(brickrun_command)
        time.sleep(5)

        return True

    def startMailbox(self):
        client = BluetoothMailboxClient()

        self.pixel_mbox = TextMailbox("pixel", client)
        self.comm_mbox = TextMailbox("comm", client)
        
        self.insertInfoTextBox("msg", "Connection to EV3 Mailbox is attempted...")
        waitTime = 2
        for attempt in range(3):
            try:
                client.connect(EV3_MAILBOX_SERVER)
                break
            except Exception:
                if attempt < 2:
                    self.insertInfoTextBox("warning", f"Connection to EV3 Mailbox failed (attempt {attempt+1}/3). Retrying in {waitTime}s...")
                    print("1")
                    time.sleep(waitTime)
                    print("2")
                    waitTime += 2
                else:
                    return False
        
        time.sleep(1)
        self.insertInfoTextBox("msg", "The programme was started successfully and a connection to the EV3 mailbox was established.")
        time.sleep(1)

        return True

        #-----------------------------------------------------------------

    def startPrinting(self):
        self.pixel_mbox.send("run")
        self.insertInfoTextBox("msg", "Printing has started...")

        self.resetManageButton()
        self.startTime = time.time()
        self.progressAnimation()
        self.timeAnimation()
        threading.Thread(target=self.receiveMessages, daemon=True).start()
        threading.Thread(target=self.printingDataProcessing, daemon=True).start()

    #---------------------------------------------------------------------

    def printingDataProcessing(self):
        totalNeedCount = sum(self.master.needItemCount.values())
        totalPlacedCount = 0

        while True:
            self.pixel_mbox.wait()
            data = self.pixel_mbox.read()
            data = eval(data)

            if len(data) == 3:
                x, y = map(int, data[1].split(","))
                cord = (x, 31-y)
                color = data[2]

            if data[0] == "finished":
                self.isPaused = True
                self.progressAnimationBar.set(1)
                hours, remainder = divmod((time.time() - self.startTime), 3600)
                minutes, seconds = divmod(remainder, 60)
                self.progressRemainingTimeLabel.configure(
                    text=f"    -    Finished after {int(hours)} hours, {int(minutes)} minutes and {seconds:.0f} seconds.")
                self.manageButton.configure(state="disabled")
                self.exitButton.configure(text="Exit")
                self.insertInfoTextBox("msg", "The EV3 has finished printing.")
                break

            elif data[0] == "couldnt placed":
                self.printingImage.putpixel(cord, (255, 0, 0))

                self.insertInfoTextBox("warning", f"{cord}, {color} could not be placed after 3 attempts.")

            elif data[0] == "couldnt placed with stone":
                self.pause(True)
                self.printingImage.putpixel(cord, (255, 0, 0))
                self.insertInfoTextBox("warning", f"{cord}, {color} could not be placed after 3 attempts.")
                self.insertInfoTextBox("warning", "Please remove the stone on the placement arm.")
                
            elif data[0] == "multiple stones":
                self.pause(True)
                self.printingImage.putpixel(cord, (255, 0, 0))
                self.insertInfoTextBox("warning", "The EV3 has picked up multiple stones.")
                self.insertInfoTextBox("warning", "Please remove the stones on the placement arm.")

            elif data[0] == "no stone":
                self.pause(True)
                self.insertInfoTextBox("warning", f"The EV3 could not pick up {color}.")
                self.insertInfoTextBox("warning", "Please check the storage location of the stone.")


            elif data[0] == "placed":
                self.printingImage.putpixel(cord, COLOR_LIST[color])

                self.master.placedItemCount[color] += 1
                self.updateItemCount()
                
            totalPlacedCount += 1

            processPercentage = totalPlacedCount / totalNeedCount
            self.progressBar.set(processPercentage)
            self.progressPercentageLabel.configure(text=f"{processPercentage*100:.0f}%")

            betweenTime = time.time() - self.startTime
            timeOnePart = betweenTime / totalPlacedCount
            self.remainingPrintingTime = (totalNeedCount - totalPlacedCount) * timeOnePart

            image = self.printingImage.resize((320,320), Image.NEAREST)
            printingCTkImg = ctk.CTkImage(light_image=image, dark_image=image, size=(320, 320))
            self.printLabel.configure(image=printingCTkImg)

    #---------------------------------------------------------------------

    def timeAnimation(self):
        if self.remainingPrintingTime != None and self.remainingPrintingTime > 0 and not self.isPaused:
            self.remainingPrintingTime -= 1

            hours, remainder = divmod(self.remainingPrintingTime, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.progressRemainingTimeLabel.configure(text=f"    -    {int(hours)} hours, {int(minutes)} minutes and {seconds:.0f} seconds remaining.")

        self.after(1000, self.timeAnimation)

    def progressAnimation(self):
        if not self.isPaused:
            self.progressAnimationValue += 0.01
            
            if self.progressAnimationValue >= 1:
                self.progressAnimationValue = 0
            
            self.progressAnimationBar.set(self.progressAnimationValue)
        
        self.after(6, self.progressAnimation)

    #---------------------------------------------------------------------

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

    def insertInfoTextBox(self, type, text):
        self.infoTextBox.configure(state="normal")
        time = datetime.datetime.now()
        time = time.strftime("%H:%M:%S")

        if type == "msg":
            self.infoTextBox.insert("end", f"\n[{time}] " + text)
        elif type == "warning":
            self.infoTextBox.insert("end", f"\n[{time}] ⚠️ [Warning] " + text)
        elif type == "error":
            self.infoTextBox.insert("end", f"\n[{time}] ❌ [ERROR] " + text)

        self.infoTextBox.see("end")
        self.infoTextBox.configure(state="disabled")

    #---------------------------------------------------------------------

    def receiveMessages(self):
        while True:
            self.comm_mbox.wait()
            msg = self.comm_mbox.read()

            if msg == "refill":
                self.refill()

            elif msg == "recalibration":
                self.recalibration()
                self.comm_mbox.wait()
                msg = self.comm_mbox.read()
                if msg == "recalibrated":
                    self.insertInfoTextBox("msg", "Recalibration of the EV3 is complete.")
                    self.insertInfoTextBox("msg", "Printing is continued...")
                    self.manageButton.configure(state="normal")

            elif msg == "pause":
                self.pause(True)

    def speedVarChange(self, *args):
        speed = self.speedVar.get()
        if speed == "" or speed == None:
            return
        self.comm_mbox.send("speed:" + str(speed))

    def parallelAxisVarChange(self, *args):
        parallelAxis = self.parallelAxisVar.get()
        self.comm_mbox.send("parallelAxis:" + str(parallelAxis))

#-------------------------------------------------------------------------

if __name__ == "__main__":
    app = App()
    app.mainloop()