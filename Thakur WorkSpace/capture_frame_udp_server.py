import io
import socket
import pickle
from picamera2 import Picamera2
import time
from datetime import datetime
from threading import Thread
from queue import Queue

# Server's hostname or IP address
SERVER_IP = '192.168.1.8'
# The port used by the server
SERVER_PORT = 8888
server_address = SERVER_IP
server_port = SERVER_PORT


# Define start and end signals
start_signal = b"START_IMAGE"
end_signal = b"END_IMAGE"

# Thread-safe queue
image_queue = Queue()

def capture_images(queue):

    # Create a Picamera2 object
    picamera2 = Picamera2()
    
    # Preview configuration (optional, for adjusting settings before capture)
    preview_config = picamera2.create_preview_configuration()
    picamera2.configure(preview_config)
    #Allow some time for sensor to adjust to conditions
    time.sleep(2)
    # Configure the camera for still capture with a specific resolution
    capture_config = picamera2.create_still_configuration(buffer_count=10)
    # capture_config = picamera2.create_still_configuration()
    capture_config["main"]["size"] = (1280, 720)  # Set the desired resolution here
    picamera2.set_controls({'ExposureTime': 1})
    picamera2.set_controls({'FrameRate': 50})
    #capture_config["main"]["framerate"] = 60
    print(capture_config)
    picamera2.configure(capture_config)
    picamera2.start()
    
    # Print camera controls
    print("Camera Controls:")
    # controls = picamera2.list_controls()
    for control in picamera2.camera_controls:
         print(f"{control}: {picamera2.camera_controls[control]}")

    print(f"Exposure Time: {picamera2.camera_controls['ExposureTime']}")

    while True:
        image = io.BytesIO()
        picamera2.capture_file(image, format='jpeg')
        timestamp = datetime.now()
        queue.put((image, timestamp))
        #time.sleep(1 / 30)  # Adjust based on your fps requirement

def send_image_via_udp(queue, server_address, server_port):
    while True:
        if not queue.empty():
            # Check the number of items in the queue
            num_images = queue.qsize()
            print(f"Number of images in the queue: {num_images}")
            image, timestamp = queue.get()
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            data = pickle.dumps((image.getvalue(), str(timestamp)))  # Convert BytesIO and timestamp to bytes
            # Send start signal
            #start_signal =  pickle.dumps("START_IMAGE")
            client_socket.sendto(start_signal, (server_address, server_port))
            chunks = [data[i:i+65507] for i in range(0, len(data), 65507)]
            print(f"Image size send to server {image.getbuffer().nbytes } bytes.")
            for chunk in chunks:
                client_socket.sendto(chunk, (server_address, server_port))
                print(f"Sending chunk of size {len(chunk)} bytes.")
                #time.sleep(1/25)
            # Send end signal
            #end_signal =pickle.dumps("END_IMAGE")
            client_socket.sendto(end_signal, (server_address, server_port))
            client_socket.close()
        else:
            time.sleep(0.001)
            #print("No image is in the queue to send the server")

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
