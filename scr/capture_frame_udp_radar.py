from subprocess import Popen, PIPE
from io import BytesIO
import socket
import pickle
from picamera2 import Picamera2
import time
from datetime import datetime
from threading import Thread
from queue import Queue
import hashlib
from picamera2.controls import Controls
import io
from PIL import Image




import sys
sys.path.append('/home/rpi/myenv/lib/python3.11/site-packages')
import ffmpeg


import serial
import numpy as np
import pyqtgraph as pg
from PyQt5.QtWidgets import QApplication
from pyqtgraph.Qt import QtCore, QtGui

import os    #impor the system 

# Server's hostname or IP address
#192.168.1.33:8888
SERVER_IP = '192.168.1.8'
#SERVER_IP = '192.168.1.33'
# The port used by the server
SERVER_PORT = 8888
server_address = SERVER_IP
server_port = SERVER_PORT

# Define start and end signals
start_signal = b"START_IMAGE"
end_signal = b"END_IMAGE"

# Thread-safe queue
image_queue = Queue()

# Track timestamps for FPS calculation
last_capture_time = time.time()
last_send_time = time.time()
captured_frames = 0
sent_frames = 0

#Radar Setup here

# Change the configuration file name if needed
configFileName = 'AWR1843config.cfg'

CLIport = {}
Dataport = {}
byteBuffer = np.zeros(2**15,dtype='uint8')
byteBufferLength = 0

s ={}
p= {}
win ={}
app ={}
# ------------------------------------------------------------------

# Function to configure the serial ports and send the data from
# the configuration file to the radar

def serialConfig(configFileName):
    #print("from the Serial and device config")
    global CLIport
    global Dataport
    # Open the serial ports for the configuration and the data ports
    
    # Check if the ports exist
    ports = ["/dev/ttyACM0", "/dev/ttyACM1"]
    for port in ports:
        if os.path.exists(port):
            print(f"Port {port} found.")
        else:
            print(f"Port {port} not found.")
            return None, None  # Return None if any port is not found
    
    # Raspberry pi
    CLIport = serial.Serial('/dev/ttyACM0', 115200)
    Dataport = serial.Serial('/dev/ttyACM1', 921600)
    configParameters ={}
    # Windows
    #CLIport = serial.Serial('COM8', 115200)
    #Dataport = serial.Serial('COM9', 921600)

    # Read the configuration file and send it to the board
    config = [line.rstrip('\r\n') for line in open(configFileName)]
    for i in config:
        CLIport.write((i+'\n').encode())
        print(i)
        time.sleep(0.01)
        
    return CLIport, Dataport

# ------------------------------------------------------------------


# Function to parse the data inside the configuration file
def parseConfigFile(configFileName):
    #print("from the parseConfigFile")
    configParameters = {} # Initialize an empty dictionary to store the configuration parameters
    
    # Read the configuration file and send it to the board
    config = [line.rstrip('\r\n') for line in open(configFileName)]
    for i in config:
        
        # Split the line
        splitWords = i.split(" ")
        
        # Hard code the number of antennas, change if other configuration is used
        numRxAnt = 4
        numTxAnt = 3
        
        # Get the information about the profile configuration
        if "profileCfg" in splitWords[0]:
            startFreq = int(float(splitWords[2]))
            idleTime = int(splitWords[3])
            rampEndTime = float(splitWords[5])
            freqSlopeConst = float(splitWords[8])
            numAdcSamples = int(splitWords[10])
            numAdcSamplesRoundTo2 = 1;
            
            while numAdcSamples > numAdcSamplesRoundTo2:
                numAdcSamplesRoundTo2 = numAdcSamplesRoundTo2 * 2;
                
            digOutSampleRate = int(splitWords[11]);
            
        # Get the information about the frame configuration    
        elif "frameCfg" in splitWords[0]:
            
            chirpStartIdx = int(splitWords[1]);
            chirpEndIdx = int(splitWords[2]);
            numLoops = int(splitWords[3]);
            numFrames = int(splitWords[4]);
            framePeriodicity = float(splitWords[5]);

            
    # Combine the read data to obtain the configuration parameters           
    numChirpsPerFrame = (chirpEndIdx - chirpStartIdx + 1) * numLoops
    configParameters["numDopplerBins"] = numChirpsPerFrame / numTxAnt
    configParameters["numRangeBins"] = numAdcSamplesRoundTo2
    configParameters["rangeResolutionMeters"] = (3e8 * digOutSampleRate * 1e3) / (2 * freqSlopeConst * 1e12 * numAdcSamples)
    configParameters["rangeIdxToMeters"] = (3e8 * digOutSampleRate * 1e3) / (2 * freqSlopeConst * 1e12 * configParameters["numRangeBins"])
    configParameters["dopplerResolutionMps"] = 3e8 / (2 * startFreq * 1e9 * (idleTime + rampEndTime) * 1e-6 * configParameters["numDopplerBins"] * numTxAnt)
    configParameters["maxRange"] = (300 * 0.9 * digOutSampleRate)/(2 * freqSlopeConst * 1e3)
    configParameters["maxVelocity"] = 3e8 / (4 * startFreq * 1e9 * (idleTime + rampEndTime) * 1e-6 * numTxAnt)
    
    return configParameters
   
# ------------------------------------------------------------------
# Function to compress image using ffmpeg
def compress_image(input_image):
    # Create a BytesIO object to store the compressed image
    compressed_image = BytesIO()
    
    # Print size of original image
    original_size = len(input_image.getvalue())
    print("Size of original image:", original_size, "bytes")
    
    # Compress the image using ffmpeg
    fps, duration = 1, 1
    p = Popen(['ffmpeg', '-y', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-r', str(fps), '-i', '-', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-r', str(fps), '-f', 'image2pipe', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    for i in range(fps * duration):
        input_image.seek(0)
        #print("here")
        p.stdin.write(input_image.read())
    p.stdin.close()
    
    # Read compressed image from ffmpeg's stdout
    compressed_image.write(p.stdout.read())
    p.stdout.close()
    
    # Print size of compressed image
    compressed_size = len(compressed_image.getvalue())
    print("Size of compressed image:", compressed_size, "bytes")
    
    return compressed_image


# Function to read and parse the incoming data
def readAndParseData18xx(Dataport, configParameters):
    #print("readAndParseData function")
    global byteBuffer, byteBufferLength
    
    # Constants
    OBJ_STRUCT_SIZE_BYTES = 12;
    BYTE_VEC_ACC_MAX_SIZE = 2**15;
    MMWDEMO_UART_MSG_DETECTED_POINTS = 1;
    MMWDEMO_UART_MSG_RANGE_PROFILE   = 2;
    maxBufferSize = 2**15;
    tlvHeaderLengthInBytes = 8;
    pointLengthInBytes = 16;
    magicWord = [2, 1, 4, 3, 6, 5, 8, 7]
    
    # Initialize variables
    magicOK = 0 # Checks if magic number has been read
    dataOK = 0 # Checks if the data has been read correctly
    frameNumber = 0
    detObj = {}
    
    readBuffer = Dataport.read(Dataport.in_waiting)
    byteVec = np.frombuffer(readBuffer, dtype='uint8')
    byteCount = len(byteVec)
     # Check that the buffer is not full, and then add the data to the buffer
    if (byteBufferLength + byteCount) < maxBufferSize:
        byteBuffer[byteBufferLength:byteBufferLength + byteCount] = byteVec[:byteCount]
        byteBufferLength = byteBufferLength + byteCount
    else:
        byteBufferLength=0
        
    # Check that the buffer has some data

    # Check that the buffer has some data
    if byteBufferLength > 16:
        try:
            # Check for all possible locations of the magic word
            possibleLocs = np.where(byteBuffer == magicWord[0])[0]
            
            if len(possibleLocs) ==0:
                print("Magic word not found in the buffer.")
                return False,frameNumber,{}
            # Confirm that is the beginning of the magic word and store the index in startIdx
            
            startIdx = []
            for loc in possibleLocs:
                check = byteBuffer[loc:loc+8]
                if np.all(check == magicWord):
                    startIdx.append(loc)
                   
            # Check that startIdx is not empty
            if startIdx:
                
                # Remove the data before the first start index
                if startIdx[0] > 0 and startIdx[0] < byteBufferLength:
                    byteBuffer[:byteBufferLength-startIdx[0]] = byteBuffer[startIdx[0]:byteBufferLength]
                    byteBuffer[byteBufferLength-startIdx[0]:] = np.zeros(len(byteBuffer[byteBufferLength-startIdx[0]:]),dtype='uint8')
                    byteBufferLength = byteBufferLength - startIdx[0]
                    
                # Check that there have no errors with the byte buffer length
                if byteBufferLength < 0:
                    byteBufferLength = 0
                    
                # word array to convert 4 bytes to a 32 bit number
                word = [1, 2**8, 2**16, 2**24]
                
                # Read the total packet length
                totalPacketLen = np.matmul(byteBuffer[12:12+4], word)
                
                # Check that all the packet has been read
                if (byteBufferLength >= totalPacketLen) and (byteBufferLength != 0):
                    magicOK = 1

                    # If magicOK is equal to 1 then process the message
                    if magicOK:
                        # word array to convert 4 bytes to a 32 bit number
                        word = [1, 2**8, 2**16, 2**24]

                        # Initialize the pointer index
                        idX = 0

                        # Read the header
                        magicNumber = byteBuffer[idX:idX+8]
                        idX += 8
                        version = format(np.matmul(byteBuffer[idX:idX+4], word), 'x')
                        idX += 4
                        totalPacketLen = np.matmul(byteBuffer[idX:idX+4], word)
                        idX += 4
                        platform = format(np.matmul(byteBuffer[idX:idX+4], word), 'x')
                        idX += 4
                        frameNumber = np.matmul(byteBuffer[idX:idX+4], word)
                        idX += 4
                        timeCpuCycles = np.matmul(byteBuffer[idX:idX+4], word)
                        idX += 4
                        numDetectedObj = np.matmul(byteBuffer[idX:idX+4], word)
                        idX += 4
                        numTLVs = np.matmul(byteBuffer[idX:idX+4], word)
                        idX += 4
                        subFrameNumber = np.matmul(byteBuffer[idX:idX+4], word)
                        idX += 4

                        # Read the TLV messages
                        for tlvIdx in range(numTLVs):

                            # word array to convert 4 bytes to a 32 bit number
                            word = [1, 2**8, 2**16, 2**24]

                            # Check the header of the TLV message
                            tlv_type = np.matmul(byteBuffer[idX:idX+4], word)
                            idX += 4
                            tlv_length = np.matmul(byteBuffer[idX:idX+4], word)
                            idX += 4

                            # Read the data depending on the TLV message
                            if tlv_type == MMWDEMO_UART_MSG_DETECTED_POINTS:

                                # Initialize the arrays
                                x = np.zeros(numDetectedObj, dtype=np.float32)
                                y = np.zeros(numDetectedObj, dtype=np.float32)
                                z = np.zeros(numDetectedObj, dtype=np.float32)
                                velocity = np.zeros(numDetectedObj, dtype=np.float32)

                                for objectNum in range(numDetectedObj):

                                    # Read the data for each object
                                    x[objectNum] = byteBuffer[idX:idX + 4].view(dtype=np.float32)
                                    idX += 4
                                    y[objectNum] = byteBuffer[idX:idX + 4].view(dtype=np.float32)
                                    idX += 4
                                    z[objectNum] = byteBuffer[idX:idX + 4].view(dtype=np.float32)
                                    idX += 4
                                    velocity[objectNum] = byteBuffer[idX:idX + 4].view(dtype=np.float32)
                                    idX += 4

                                # Store the data in the detObj dictionary
                                detObj = {"numObj": numDetectedObj, "x": x, "y": y, "z": z, "velocity": velocity}
                                dataOK = 1

                        # Remove already processed data
                        if idX > 0 and byteBufferLength > idX:
                            shiftSize = totalPacketLen


                            byteBuffer[:byteBufferLength - shiftSize] = byteBuffer[shiftSize:byteBufferLength]
                            byteBuffer[byteBufferLength - shiftSize:] = np.zeros(len(byteBuffer[byteBufferLength - shiftSize:]), dtype='uint8')
                            byteBufferLength = byteBufferLength - shiftSize

                            # Check that there are no errors with the buffer length
                            if byteBufferLength < 0:
                                byteBufferLength = 0
        except ValueError as e:
            print("ValueError occurred:",e)
            byteBufferLength=0
            return False,frameNumber,{}

    return dataOK, frameNumber, detObj

# Funtion to update the data and display in the plot
def update():
    # Read and parse the received data
    dataOk, frameNumber, detObj = readAndParseData18xx(Dataport, configParameters)
    
#    if dataOk and len(detObj["x"]) > 0:
        
        # Print information about each detected object
#         print("Number of objects detected:", detObj["numObj"])
#         for i in range(detObj["numObj"]):
#             print(f"Object {i+1}:")
#             print(f"  - Position: ({detObj['x'][i]}, {detObj['y'][i]}, {detObj['z'][i]})")
#             print(f"  - Distance: {np.linalg.norm([detObj['x'][i], detObj['y'][i], detObj['z'][i]])} meters")
#             print(f"  - Velocity: {detObj['velocity'][i]} m/s")
#             print()
        
        # Update the plot
#         x = -detObj["x"]
#         y = detObj["y"]
#         s.setData(x, y)
#         app.processEvents()
    
    return dataOk
    
def calculate_hash(data):
    return hashlib.sha256(data).hexdigest()

def capture_images(queue):
    global last_capture_time, captured_frames,configParameters,p,s,win,app
    
    print("Starting of the camere Seeting>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>")
    # Create a Picamera2 object
    picamera2 = Picamera2()
    
    # Preview configuration (optional, for adjusting settings before capture)
    preview_config = picamera2.create_preview_configuration()
    picamera2.configure(preview_config)
    # Allow some time for sensor to adjust to conditions
    time.sleep(1)
    # Configure the camera for still capture with a specific resolution
    capture_config = picamera2.create_still_configuration(buffer_count=10)
    # capture_config = picamera2.create_still_configuration()
    # capture_config["main"]["size"] = (1280, 720)  # Set the desired resolution here
    capture_config["main"]["size"] = (1280, 720)
    picamera2.set_controls({'ExposureTime': 1})
    picamera2.set_controls({'FrameRate': 30})
    picamera2.configure(capture_config)
    with picamera2.controls as ctrl:
        ctrl.AnalogueGain = 0.6
        ctrl.ExposureTime = 30000
    ctrls = Controls(picamera2)
    # capture_config["main"]["framerate"] = 60
    print(capture_config)
   
    picamera2.start()
    time.sleep(2)
    # Print camera controls
    print("Camera Controls:")
    # controls = picamera2.list_controls()
    for control in picamera2.camera_controls:
         print(f"{control}: {picamera2.camera_controls[control]}")

    print(f"Exposure Time: {picamera2.camera_controls['ExposureTime']}")
    
    
    print("End of the camera Seeting>>>>>>>>")
    print("Start the Radar Seeting..................");
    # Configurate the serial port
    CLIport, Dataport = serialConfig(configFileName)

    # Get the configuration parameters from the configuration file
    configParameters = parseConfigFile(configFileName)

    # START QtAPPfor the plot
    #app = QApplication([])
    
#     pg.setConfigOption('background', 'w')
#     win = pg.GraphicsLayoutWidget(title="2D scatter plot")
#     p = win.addPlot()
#     p.setXRange(-0.5, 0.5)
#     p.setYRange(0, 1.5)
#     p.setLabel('left', text='Y position (m)')
#     p.setLabel('bottom', text='X position (m)')
#     #s = p.plot([], [], pen=None, symbol='o')
    #win.show()
    # Main loop 
    detObj = {}  
    frameData = {}    
    currentIndex = 0
    
    radar_frame_count =0;
    
    while True:
        
        try:
            # Update the data and check if the data is okay
            #dataOk = update()
            object_data = []  # List to store data for each detected object
            dataOk, frameNumber, detObj = readAndParseData18xx(Dataport, configParameters)
            if dataOk and len(detObj["x"]) > 0:
                radar_frame_count +=1;
                for i in range (detObj["numObj"]):
                    # Store position data
                    position = (detObj['x'][i], detObj['y'][i], detObj['z'][i])
                    #calculate distance
                    distance = np.linalg.norm([detObj['x'][i], detObj['y'][i], detObj['z'][i]])
                    #Store Velocity data
                    velocity = detObj['velocity'][i]
                    # Store data for current object in a dictionary
                    object_info = {
                        "position": position,
                        "distance": distance,
                        "velocity": velocity
                    }
                    
                # Append object_info to the object_data list
                    object_data.append(object_info)
                image = io.BytesIO()
                picamera2.capture_file(image, format='jpeg')
                #image.seek(0)
                #output_image = compress_image(image)
                timestamp = datetime.now()
                #print("Capture timeStamp:",timestamp)
                
        #         print("capture frame",captured_frames);
                # Calculate FPS for captureS
                current_time = time.time()
                time_diff = current_time - last_capture_time
                if time_diff >= 1.0:
                    capture_fps = captured_frames / time_diff
                    radar_fps = radar_frame_count/time_diff;
                    print(f"Capture FPS: {capture_fps:.2f}")
                    print(f"Radar FPS: {radar_fps:.2f}")
                    last_capture_time = current_time
                    captured_frames = 0
                    radar_frame_count =0
                else:
                    captured_frames += 1
                queue.put((image, timestamp,image.getbuffer().nbytes,object_data))
                # Stop the program and close everything if Ctrl + c is pressed
        except KeyboardInterrupt:
                CLIport.write(('sensorStop\n').encode())
                CLIport.close()
                Dataport.close()
                win.close()
                break
        
        
def send_image_via_udp(queue, server_address, server_port):
    global last_send_time, sent_frames
    while True:
        # Check the number of items in the queue
        #print(f"Number of images in the queue: {queue.qsize()}")
        image, timestamp, image_size,radar_data = queue.get()
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        image_data = image.getvalue()
        image_size_bytes = len(image_data)
        
        # here is the code to
        if image_size !=image_size_bytes:
             print("image size from the queue:",image_size)
             print("image size from the array:",image_size_bytes)
             continue
        data = pickle.dumps((image.getvalue(), str(timestamp),str(image_size),str(radar_data)))
        #data = pickle.dumps((image.getvalue()))
        client_socket.sendto(start_signal, (server_address, server_port))
        chunks = [data[i:i+65507] for i in range(0, len(data), 65507)]
        for chunk in chunks:
            client_socket.sendto(chunk, (server_address, server_port))
            # print(f"Sending chunk of size {len(chunk)} bytes.")
        # Send end signal
        client_socket.sendto(end_signal, (server_address, server_port))
        client_socket.close()

        # Calculate FPS for sending
        current_time = time.time()
        time_diff = current_time - last_send_time
        if time_diff >= 1.0:
            send_fps = sent_frames / time_diff
            print(f"Send FPS: {send_fps:.2f}")
            last_send_time = current_time
            sent_frames = 0
        else:
            sent_frames += 1
        # print("No image is in the queue to send the server")


def main():
    # Start the image capture thread
    capture_thread = Thread(target=capture_images, args=(image_queue,))
    capture_thread.daemon = True
    capture_thread.start()

    # Start the image sending thread
    sending_thread = Thread(target=send_image_via_udp, args=(image_queue, server_address, server_port))
    sending_thread.daemon = True
    sending_thread.start()

    capture_thread.join()
    sending_thread.join()

if __name__ == "__main__":
    main()