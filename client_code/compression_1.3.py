import io
import cv2
import numpy as np
import time
from datetime import datetime
from subprocess import Popen, PIPE
from queue import Queue
from threading import Thread
from picamera2 import Picamera2

# Global variables for calculating frame rate
last_display_time = time.time()
displayed_frames = 0

def compress_image(image):
    # Compress the image using ffmpeg
    p = Popen(['ffmpeg', '-y', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-r', '24', '-i', '-', '-q:v', '31', '-f', 'image2pipe', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
    p.stdin.write(image)
    p.stdin.close()
    compressed_image = p.stdout.read()
    p.stdout.close()

    return compressed_image

def draw_info(image, text):
    # Draw text on an image
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(image, text, (10, 25), font, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    return image

def display_images(original, compressed, timestamp, compression_ratio, frame_rate):
    global displayed_frames, last_display_time

    # Convert byte data to NumPy array for original and compressed images
    nparr_original = np.frombuffer(original, np.uint8)
    original_image = cv2.imdecode(nparr_original, cv2.IMREAD_COLOR)

    nparr_compressed = np.frombuffer(compressed, np.uint8)
    compressed_image = cv2.imdecode(nparr_compressed, cv2.IMREAD_COLOR)

    # Prepare text to display on images
    info_text_original = f"Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}, FPS: {frame_rate:.2f}"
    info_text_compressed = f"Compression Ratio: {compression_ratio:.2f}:1"

    # Draw information on images
    original_image = draw_info(original_image, f"Original - {info_text_original}")
    compressed_image = draw_info(compressed_image, f"Compressed - {info_text_compressed}")

    # Display the original and compressed images
    cv2.imshow('Original Image', original_image)
    cv2.imshow('Compressed Image', compressed_image)

    cv2.waitKey(1)  # Refresh the windows

def capture_images(queue):
    global displayed_frames, last_display_time

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

        queue.put((original_image_data, timestamp, frame_rate))

if __name__ == "__main__":
    image_queue = Queue()
    capture_thread = Thread(target=capture_images, args=(image_queue,))
    capture_thread.daemon = True
    capture_thread.start()

    try:
        while True:
            original, timestamp, frame_rate = image_queue.get()

            compressed = compress_image(original)
            compression_ratio = len(original) / len(compressed)

            display_images(original, compressed, timestamp, compression_ratio, frame_rate)
    except KeyboardInterrupt:
        print("Stopping...")
    finally:
        cv2.destroyAllWindows()
