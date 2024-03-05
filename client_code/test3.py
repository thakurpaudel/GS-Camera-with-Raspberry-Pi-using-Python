import socket
import pickle
from picamera2 import Picamera2
import time
from datetime import datetime
import io
# Server's hostname or IP address
SERVER_IP = '192.168.1.8'
# The port used by the server
SERVER_PORT = 8888

def send_image_via_udp(image, server_address, server_port):
    # Create a UDP socket
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Serialize the image and timestamp using pickle
        data = pickle.dumps(image)
        # Determine the maximum packet size
        max_packet_size = 65507  # Maximum UDP packet size
        # Split the data into chunks
        chunks = [data[i:i+max_packet_size] for i in range(0, len(data), max_packet_size)]
        # Send each chunk to the server
        for chunk in chunks:
            client_socket.sendto(chunk, (server_address, server_port))
        # Send termination signal after all chunks are sent
        client_socket.sendto(b'TERMINATE', (server_address, server_port))
    except Exception as e:
        print("Error sending image:", e)
    finally:
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
    capture_config["main"]["size"] = (1280, 720)  # Set the desired resolution here
    picamera2.configure(capture_config)
    picamera2.start()
    capture_duration = 1  # Capture for 1 second
    frames_to_capture = int(30 * capture_duration)  # Assuming 30 fps
    timestamps = []  # List to store timestamps
    start_time = time.time()
    for i in range(frames_to_capture):
        data = io.BytesIO()
        picamera2.capture_file(data, format='jpeg')
        timestamp = datetime.now()  # Capture timestamp
        timestamps.append(timestamp)
        send_image_via_udp(data, SERVER_IP, SERVER_PORT)
        #time.sleep(1 / 30)  # Adjust this value as needed for desired FPS
    elapsed_time = time.time() - start_time
    print(f"Done capturing images. Total time: {elapsed_time}s, Captured frames: {frames_to_capture}")
    picamera2.stop()

if __name__ == "__main__":
    main()
