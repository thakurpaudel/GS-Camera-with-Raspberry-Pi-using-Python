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



def calculate_hash(data):
    return hashlib.sha256(data).hexdigest()

def capture_images(queue):
    global last_capture_time, captured_frames
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

    while True:
        image = io.BytesIO()
        picamera2.capture_file(image, format='jpeg')
        #image.seek(0)
        #output_image = compress_image(image)
        timestamp = datetime.now()
        #print("Capture timeStamp:",timestamp)
        queue.put((image, timestamp,image.getbuffer().nbytes))
        
        # Calculate FPS for captureS
        current_time = time.time()
        time_diff = current_time - last_capture_time
        if time_diff >= 1.0:
            capture_fps = captured_frames / time_diff
            print(f"Capture FPS: {capture_fps:.2f}")
            last_capture_time = current_time
            captured_frames = 0
        else:
            captured_frames += 1


def send_image_via_udp(queue, server_address, server_port):
    global last_send_time, sent_frames
    while True:
        # Check the number of items in the queue
        # print(f"Number of images in the queue: {num_images}")
        image, timestamp, image_size = queue.get()
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        image_data = image.getvalue()
        image_size_bytes = len(image_data)
        
        # here is the code to
        if image_size !=image_size_bytes:
             print("image size from the queue:",image_size)
             print("image size from the array:",image_size_bytes)
             continue
        data = pickle.dumps((image.getvalue(), str(timestamp),str(image_size)))
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
