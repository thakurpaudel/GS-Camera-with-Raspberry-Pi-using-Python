import socket
import pickle
from PIL import Image, ImageTk, ImageDraw, ImageFont
import io
import tkinter as tk
import threading
from datetime import datetime
from queue import Queue
import time



# Server configuration
SERVER_IP = '0.0.0.0'  # Listen on all available network interfaces
SERVER_PORT = 8888

# Global variables
image_queue = Queue()
start_signal = b"START_IMAGE"
end_signal = b"END_IMAGE"



#DEFAULT_FONT = ImageFont.load_default()
def get_ip_address():
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
    return ip_address

#this the the therd used to receive the image 
def receive_image_from_udp(server_ip, server_port, label):
    # Create a UDP socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Bind the socket to the server address and port
    server_socket.bind((server_ip, server_port))
    print("UDP server up and listening at {}:{}".format(get_ip_address(), SERVER_PORT))
    print("UDP server is listening...")

    receiving_image = False
    buffer = bytearray()
    captured_frames = 0
    last_capture_time = time.time()
    while True:
        data, address = server_socket.recvfrom(65507)  # Maximum UDP packet size
        
        # Check for the start signal
        if data.startswith(start_signal):
            receiving_image = True
            buffer = bytearray()  # Reset/Initialize buffer
            current_time = datetime.now()
            continue
        
        # Check for the end signal
        if data.startswith(end_signal):
            current_time = time.time()
            time_diff = current_time - last_capture_time
            if time_diff >= 1.0:
                capture_fps = captured_frames / time_diff
                print(f"Frame Received FPS: {capture_fps:.2f}")
                last_capture_time = current_time
                captured_frames = 0
            else:
                captured_frames += 1
            receiving_image = False
            max_size = 10*1024*1024
            if len(buffer)<max_size:
                try:
                    image = pickle.loads(buffer)  # Attempt to unpickle the data
                    image_queue.put(image)  # Add the completed image to the queue
                except UnicodeDecodeError as e:
                    print("Error decoding received data:", e)
                except EOFError:
                    #image_queue.queue.clear()
                    print("Error: Ran out of input while unpickling data")
                except pickle.UnpicklingError as e:
                    print("Error unpickling data:", e)
                except Exception as e:
                    print("An unexpected error occurred:", e)
            buffer.clear()  # Clear the buffer after processing the image
            continue
        
        # If currently receiving an image, append data to buffer
        if receiving_image:
            buffer.extend(data)

def display_images(label):
    last_display_time = datetime.now()
    frames_since_last_display = 0
    fps = 0  # Initialize fps outside the loop
    frame_size = "N/A"  # Initialize frame size outside the loop
    while True:
        if not image_queue.empty():
            image_bytes, timestamp,image_size = image_queue.get()
            i =0
            print("Capture Image, Radar Data Time Stamp:", timestamp)
            print("Current Time :",datetime.now())
            time_diff = datetime.now() - timestamp
            print("Lag in the time:",time_diff.total_seconds())
            print("Received frame Rate Per seconds:",capture_fps)
            frame_size = f"{Image.open(io.BytesIO(image_bytes)).size}"
            print("Image size from the Camera :",frame_size)
            
            if len(radar_data) > 0:
                 for obj in radar_data:
                     # Extract the position, velocity, and distance for the current object
                     position = obj['position']
                     velocity = obj['velocity']
                     distance = obj['distance']
                     print(f"Position: {position}, Velocity: {velocity}, Distance: {distance}")
            print("queue size:",image_queue.qsize())
            image_queue.queue.clear()
            continue
#             if int(image_size) != len(image_bytes):
#                 print("Error in the image received")
#                 print("Expected Image size is:",image_size)
#                 print("Received Image size is:", len(image_bytes))
#                 continue
# 
#             frames_since_last_display += 1
            
            # Calculate FPS
#             current_time = datetime.now()
#             time_difference = (current_time - last_display_time).total_seconds()
#             if time_difference >= 1:  # Update FPS every second
#                 fps = frames_since_last_display / time_difference
#                 last_display_time = current_time
#                 frames_since_last_display = 0
#                 
#             frame_size = f"{Image.open(io.BytesIO(image_bytes)).size}"  # Calculate frame size
#             display_image_with_timestamp(image_bytes, timestamp, label, fps, frame_size)
#             image_queue.queue.clear()
#         else:
#             print("No image for the display")
            # If the image queue is empty, set FPS and frame size to N/A
            #display_image_with_timestamp(b"", "", label, 0, "N/A")


def update_image(image_bytes, timestamp, label, fps, frame_size):
    try:
        # Convert bytes to image
        image = Image.open(io.BytesIO(image_bytes))

        # Add timestamp, FPS, and frame size to the image
            # Add timestamp, FPS, and frame size to the image
        draw = ImageDraw.Draw(image)
        font = ImageFont.load_default()  # Use the system default font
#         time_format = "Image Capture Time:" + str(timestamp)
#         draw.text((10, 10), str(time_format), fill="black", font=font)

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        image_size_kb = len(image_bytes) / 1024
        draw.text((10, 30), f"Image Capture Time: {timestamp}\nTime: {current_time}\nSize: {image_size_kb:.2f} KB\nFPS: {fps:.2f}\nFrame Size: {frame_size}", fill="black", font=font)
    
        photo = ImageTk.PhotoImage(image)

        # Update the label with the new image
        label.configure(image=photo)
        label.image = photo  # Keep a reference
    except Exception as e:
        print("Error updating label with image:", e)
def display_image_with_timestamp(image_bytes, timestamp, label, fps, frame_size):
      label.after(0, update_image, image_bytes, timestamp, label, fps, frame_size)
#     try:
#         # Convert bytes to image
#         print("here")
#         image = Image.open(io.BytesIO(image_bytes))
# 
#         # Add timestamp, FPS, and frame size to the image
#         draw = ImageDraw.Draw(image)
#         draw.text((10, 10), f"Image Capture Time: {timestamp}", fill="white", font=DEFAULT_FONT)
#         draw.text((10, 30), f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill="white", font=DEFAULT_FONT)
#         image_size_kb = len(image_bytes) / 1024
#         draw.text((10, 50), f"Size: {image_size_kb:.2f} KB", fill="white", font=DEFAULT_FONT)
#         draw.text((10, 70), f"FPS: {fps:.2f}", fill="white", font=DEFAULT_FONT)  # Display FPS
#         draw.text((10, 90), f"Frame Size: {frame_size}", fill="white", font=DEFAULT_FONT)  # Display frame size
# 
#         # Convert image to Tkinter format
#         photo = ImageTk.PhotoImage(image)
# 
#         # Update the label with the new image using the main thread
#         label.after(0, lambda: label.configure(image=photo))
#     except Exception as e:
#         print("Error updating label with image:", e)
# 
#     return image
 
  
def main():
    root = tk.Tk()
    root.title("Image Receiver")
    label = tk.Label(root)
    label.pack()

    # Create and start the receive thread
    receive_thread = threading.Thread(target=receive_image_from_udp, args=(SERVER_IP, SERVER_PORT, label))
    receive_thread.daemon = True
    receive_thread.start()

    # Create and start the display thread
    display_thread = threading.Thread(target=display_images, args=(label,))
    display_thread.daemon = True
    display_thread.start()

    root.mainloop()

if __name__ == "__main__":
    main()










