import io
import cv2
import numpy as np
import time
from datetime import datetime
from subprocess import Popen, PIPE
from queue import Queue
from threading import Thread
from picamera2 import Picamera2
from picamera2.controls import Controls

# Global variables for calculating frame rate
last_display_time = time.time()
displayed_frames = 0

def compress_image(image):
    # Compress the image using ffmpeg
    current_time = time.time()
    p = Popen(['ffmpeg', '-y', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-r', '24', '-i', '-', '-q:v', '31', '-f', 'image2pipe', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.stdin.write(image)
    p.stdin.close()
    compressed_image = p.stdout.read()
    p.stdout.close()
    print("Compress time for the image:", (time.time()-current_time), "seconds")
    return compressed_image

def draw_info(image, text):
    # Draw text on an image
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(image, text, (10, 25), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    return image
def display_images(original, compressed, timestamp, compression_ratio, frame_rate, original_size, compressed_size, original_format, compressed_format):
    global displayed_frames, last_display_time

    # Convert byte data to NumPy array for original and compressed images
    nparr_original = np.frombuffer(original, np.uint8)
    original_image = cv2.imdecode(nparr_original, cv2.IMREAD_COLOR)

    nparr_compressed = np.frombuffer(compressed, np.uint8)
    compressed_image = cv2.imdecode(nparr_compressed, cv2.IMREAD_COLOR)

    # Prepare text to display on images
    info_text_original = f"Original - Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}, Size: {original_size}, Format: {original_format}"
    info_text_compressed = f"Compressed - Compression Ratio: {compression_ratio:.2f}:1, FPS: {frame_rate:.2f}, Size: {compressed_size}, Format: {compressed_format}"

    # Draw information on images
    original_image = draw_info(original_image, info_text_original)
    compressed_image = draw_info(compressed_image, info_text_compressed)

    # Display the original and compressed images
    cv2.imshow('Original Image', original_image)
    cv2.imshow('Compressed Image', compressed_image)

    cv2.waitKey(1)  # Refresh the windows
def capture_images(queue):
    global displayed_frames, last_display_time

#     picamera2 = Picamera2()
#     capture_config = picamera2.create_still_configuration()
#     picamera2.configure(capture_config)
# 
#     picamera2.start()
#     time.sleep(2)  # Allow camera to initialize
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

    while True:
        image = io.BytesIO()
        picamera2.capture_file(image, format='jpeg')  # Ensure to specify the format explicitly
        image.seek(0)
        original_image_data = image.getvalue()

        timestamp = datetime.now()

        # Calculate display FPS
        current_time = time.time()
        if displayed_frames == 0:
            last_display_time = current_time
        displayed_frames += 1
        time_diff = current_time - last_display_time
        if time_diff > 0:
            frame_rate = displayed_frames / time_diff
            if time_diff >= 1.0:
                last_display_time = current_time
                displayed_frames = 0
        else:
            frame_rate = 0

        # Get size and format of original image
        original_size = len(original_image_data)
        original_format = 'JPEG'
        print("Frame rate:", frame_rate)

        queue.put((original_image_data, timestamp, frame_rate, original_size, original_format))

if __name__ == "__main__":
    image_queue = Queue()
    capture_thread = Thread(target=capture_images, args=(image_queue,))
    capture_thread.daemon = True
    capture_thread.start()

    try:
        while True:
            original, timestamp, frame_rate, original_size, original_format = image_queue.get()
            print("image on the queue:",image_queue.qsize())
            compressed = compress_image(original)
            compressed_size = len(compressed)
            compressed_format = 'JPEG'

            compression_ratio = original_size / compressed_size

            #display_images(original, compressed, timestamp, compression_ratio, frame_rate, original_size, compressed_size, original_format, compressed_format)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        cv2.destroyAllWindows()