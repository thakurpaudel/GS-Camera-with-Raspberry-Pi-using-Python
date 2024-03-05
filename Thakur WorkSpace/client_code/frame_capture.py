# from picamera2 import Picamera2, Preview
# from libcamera import Transform
# picam2 = Picamera2()
# picam2.start_preview(Preview.QTGL, x=100, y=200, width=1024, height=720,
# transform=Transform(hflip=0,vflip=0))
# picam2.start()

# from picamera2 import Picamera2, Preview
# picam2 = Picamera2()
# picam2.start_preview(Preview.QTGL)
# 
# from picamera2 import Picamera2, Preview
# picam2 = Picamera2()
# picam2.start_preview(Preview.DRM)

# from picamera2 import Picamera2, Preview
# picam2 = Picamera2()
# picam2.start_preview(Preview.QT)

# from picamera2 import Picamera2, Preview
# picam2 = Picamera2()
# picam2.start_preview(Preview.NULL)

# from picamera2 import Picamera2, Preview
# import time
# picam2 = Picamera2()
# config = picam2.create_preview_configuration()
# picam2.configure(config)
# picam2.start()
# time.sleep(2)
# picam2.stop_preview()
# picam2.start_preview(True)
# time.sleep(2)


# from picamera2 import Picamera2
# picam2 = Picamera2()
# picam2.start(show_preview=True)
# picam2.title_fields = ["ExposureTime", "AnalogueGain"]



# from picamera2 import Picamera2
# picam2 = Picamera2()
# picam2.start_and_capture_file("takepicture.jpg")


# from picamera2 import Picamera2, Preview
# picam2 = Picamera2()
# picam2.start_preview(Preview.QT)

# from pprint import *
# from picamera2 import Picamera2, Preview
# picam2 = Picamera2()
# mode = picam2.sensor_modes[0]
# config = picam2.create_preview_configuration(sensor={'output_size': mode['size'], 'bit_depth':
# mode['bit_depth']})
# pprint(picam2.sensor_modes)
#import os
import io
import socket
import pickle  # For serializing the image and timestamp
import numpy as np
from libcamera import controls
from picamera2 import Picamera2
import time
from datetime import datetime
from PIL import Image
#import cv2  # Import OpenCV
#import warnings

# Server's hostname or IP address
#SERVER_IP = '192.168.1.33'
SERVER_IP = '192.168.1.8'

# The port used by the server
SERVER_PORT = 8888

server_address = SERVER_IP  # Change this to your server's IP address
server_port = SERVER_PORT  # Change this to the desired port

# def send_image_via_udp(image, timestamp, server_address, server_port):
#     # Create a UDP socket
#     client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
#     # Serialize the image and timestamp using pickle
#     data = pickle.dumps(image)
# 
#     # Determine the maximum packet size
#     max_packet_size = 65507  # Maximum UDP packet size
# 
#     # Split the data into chunks
#     chunks = [data[i:i+max_packet_size] for i in range(0, len(data), max_packet_size)]
# 
#     # Send each chunk to the server
#     for chunk in chunks:
#         client_socket.sendto(chunk, (server_address, server_port))
# 
#     # Close the socket
#     client_socket.close()
def send_image_via_udp(image, timestamp, server_address, server_port):
    # Create a UDP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # Serialize the image and timestamp using pickle
    data = pickle.dumps((image, timestamp))

    # Determine the maximum packet size
    max_packet_size = 65507  # Maximum UDP packet size

    # Split the data into chunks
    chunks = [data[i:i+max_packet_size] for i in range(0, len(data), max_packet_size)]
    print(f"Image size send to server {image.getbuffer().nbytes } bytes.")
    print(f"Image size send to server Total {len(chunks)} bytes.")

    # Send each chunk to the server
    for chunk in chunks:
        client_socket.sendto(chunk, (server_address, server_port))
        print(f"Sending chunk of size {len(chunk)} bytes.")
        #print(chunk)
        time.sleep(1/25)

    # Close the socket
    client_socket.close()
    
def main():
    # Create a Picamera2 object
    
    picamera2 = Picamera2()
    
    # Preview configuration (optional, for adjusting settings before capture)
    preview_config = picamera2.create_preview_configuration()
    picamera2.configure(preview_config)
    

    # Allow some time for sensor to adjust to conditions
    time.sleep(2)

    # Configure the camera for still capture with a specific resolution
    capture_config = picamera2.create_still_configuration(buffer_count=10)
#     capture_config = picamera2.create_still_configuration()
    capture_config["main"]["size"] = (1280, 720)  # Set the desired resolution here
    picamera2.set_controls({'ExposureTime': 1})
    picamera2.set_controls({'FrameRate': 50})
    #capture_config["main"]["framerate"] = 60
    print(capture_config)
    picamera2.configure(capture_config)
    picamera2.start()
    
        # Print camera controls
    print("Camera Controls:")
#     controls = picamera2.list_controls()
    for control in picamera2.camera_controls:
         print(f"{control}: {picamera2.camera_controls[control]}")

    print(f"Exposure Time: {picamera2.camera_controls['ExposureTime']}")
    #print(f"Exposure Time: {picamera2.camera_controls['FrameRate']}")

    capture_duration = 1  # Capture for 10 seconds
   
    frames_to_capture = int(100* capture_duration)  # Assuming 30 fps
# 	Pre-allocate
    images = np.empty((frames_to_capture, 720, 1280, 3), dtype=np.uint8)
    timestamps = []  # List to store timestamps
    images = []
    start_time = time.time()
    image_count =0
    start_capture_time = time.time()
    while True:
        
#     while (time.time() - start_time) < capture_duration:
        # Generate a timestamped filename
        #timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S-%f')
#         filename = f"image_{timestamp}.jpg"
        #filename = os.path.join(output_folder, f"image_{timestamp}.jpg")
        #picamera2.capture_file(filename)
    #for i in range(frames_to_capture):
        image = io.BytesIO()
        picamera2.capture_file(image, format='jpeg')
        #image = picamera2.capture_array()
        #images.append(image)
        #timestamps.append(datetime.now())  # Capture timestamp
  # Capture timestamp
        image_count +=1
        send_image_via_udp(image,datetime.now(), server_address, server_port)
        #print(f"Captured {filename}")
        #print(time.time()-time1)
        # Wait to approximate 30 fps capture rate
        time.sleep(1 / 60)  # Adjust this value as needed for processing time
    end_capture_time=time.time();
    picamera2.stop()
    elapsed_time = time.time() - start_time
    print(f"Done capturing images. Total time: {elapsed_time}s, Captured frames: {frames_to_capture}")
    print("Done capturing images.")
    print(f"Image count:{image_count}")
    print(f"total time of capture:{(end_capture_time-start_capture_time)}")
    #with warnings.catch_warnings():
        #warnings.simplefilter("ignore")
        #Displaying the captured images 
    for i, image in enumerate(images):
            #cv2.imshow('Captured Frame', image)
                    # Display size of the image
        #print(f"Image {i+1} size: {image.shape[1]}x{image.shape[0]} pixels")

            # Calculate memory size of the image
#         memory_size = image.nbytes / (1024 * 1024)  # Convert bytes to megabytes
        memory_size = image.getbuffer().nbytes / (1024 * 1024)  # Convert bytes to megabytes
            # Print memory size of the image
        print(f"Memory size of Image {i+1}: {memory_size:.2f} MB")
            # Display timestamp
        print(f"Timestamp for Image {i+1}: {timestamps[i]}")
        
#         image1 = Image.open(image)
#         image1.show()
            #cv2.waitKey(100)  # Display each frame for 100 milliseconds

    #cv2.destroyAllWindows()  # Make sure to destroy all OpenCV windows
if __name__ == "__main__":
    main()



