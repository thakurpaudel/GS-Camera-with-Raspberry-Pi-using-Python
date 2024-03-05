import io
import cv2
import numpy as np
import time
from datetime import datetime
from subprocess import Popen, PIPE
from queue import Queue
from threading import Thread
from picamera2 import Picamera2

last_capture_time = time.time()
captured_frames = 0
compressed_frames = 0
total_compression_time = 0

def compress_image(image):
    # Compress the image using ffmpeg
    p = Popen(['ffmpeg', '-y', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-r', '24', '-i', '-', '-q:v', '31', '-f', 'image2pipe', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.stdin.write(image)
    p.stdin.close()
    compressed_image = p.stdout.read()
    p.stdout.close()
    return compressed_image

def display_images(original, compressed):
    # Convert byte data to NumPy array for original image
    nparr = np.frombuffer(original, np.uint8)
    original_image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    # Convert byte data to NumPy array for compressed image
    nparr_compressed = np.frombuffer(compressed, np.uint8)
    compressed_image = cv2.imdecode(nparr_compressed, cv2.IMREAD_COLOR)

    # Display the original image
    cv2.imshow('Original Image', original_image)
    
    # Display the compressed image
    cv2.imshow('Compressed Image', compressed_image)

    cv2.waitKey(1)  # Refresh the windows

def capture_images(queue):
    global last_capture_time, captured_frames

    picamera2 = Picamera2()
    capture_config = picamera2.create_still_configuration()
    picamera2.configure(capture_config)

    picamera2.start()
    time.sleep(2)  # Allow camera to initialize

    while True:
        image = io.BytesIO()
        picamera2.capture_file(image, format='jpeg')  # Ensure to specify the format explicitly
        image.seek(0)
        original_image_data = image.getvalue()

        compressed_image_data = compress_image(original_image_data)
        queue.put((original_image_data, compressed_image_data))

        # FPS calculation for capture
        current_time = time.time()
        time_diff = current_time - last_capture_time
        if time_diff >= 1.0:
            capture_fps = captured_frames / time_diff
            print(f"Capture FPS: {capture_fps:.2f}")
            last_capture_time = current_time
            captured_frames = 0
        else:
            captured_frames += 1

if __name__ == "__main__":
    image_queue = Queue()
    capture_thread = Thread(target=capture_images, args=(image_queue,))
    capture_thread.daemon = True
    capture_thread.start()

    try:
        while True:
            original, compressed = image_queue.get()
            display_images(original, compressed)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        cv2.destroyAllWindows()