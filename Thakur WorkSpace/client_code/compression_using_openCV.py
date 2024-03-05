import io
import cv2
import numpy as np
import time
from datetime import datetime
from queue import Queue
from threading import Thread
from picamera2 import Picamera2
from picamera2.controls import Controls


last_capture_time = time.time()
captured_frames = 0


# Adjust the JPEG quality for compression
def compress_image_simple(image):
    start_time = time.time()
    # Convert image to a NumPy array
    image_np = np.frombuffer(image, dtype=np.uint8)
    image_np = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
    # Perform a simple and fast compression without changing the size
    _, buffer = cv2.imencode('.jpg', image_np, [int(cv2.IMWRITE_JPEG_QUALITY), 20])  # Adjust the quality here
    compressed_bytes = buffer.tobytes()
    print(f"Compression time: {(time.time() - start_time) * 1000:.2f} ms")
    return compressed_bytes

def display_images(original, compressed, timestamp, original_size, compressed_size):
    # Prepare windows
    cv2.namedWindow('Original Image', cv2.WINDOW_NORMAL)
    cv2.namedWindow('Compressed Image', cv2.WINDOW_NORMAL)

    # Decode images for display
    original_img = cv2.imdecode(np.frombuffer(original, np.uint8), cv2.IMREAD_COLOR)
    compressed_img = cv2.imdecode(np.frombuffer(compressed, np.uint8), cv2.IMREAD_COLOR)

    # Display metadata on images
    original_info = f"Original - Size: {original_size} bytes"
    compressed_info = f"Compressed - Size: {compressed_size} bytes"
    compression_ratio = f"Compression Ratio: {original_size/compressed_size:.2f}:1"

    cv2.putText(original_img, original_info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(compressed_img, compressed_info, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(compressed_img, compression_ratio, (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # Display images
    cv2.imshow('Original Image', original_img)
    cv2.imshow('Compressed Image', compressed_img)
    cv2.waitKey(1)

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

    while True:
        image = io.BytesIO()
        picamera2.capture_file(image, format='jpeg')
        image.seek(0)
        original_image_data = image.getvalue()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        original_size = len(original_image_data)
        compressed_image=compress_image_simple(original_image_data)
        queue.put((original_image_data, timestamp, original_size,compressed_image))
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

if __name__ == "__main__":
    image_queue = Queue()
    capture_thread = Thread(target=capture_images, args=(image_queue,))
    capture_thread.daemon = True
    capture_thread.start()

    try:
        while True:
            if not image_queue.empty():
                original, timestamp, original_size,compressed = image_queue.get()
                print("Image in the qeue to display", image_queue.qsize())
                #compressed = compress_image_simple(original)
                compressed_size = len(compressed)
                display_images(original, compressed, timestamp, original_size, compressed_size)
    except KeyboardInterrupt:
        print("Stopping...")
        cv2.destroyAllWindows()