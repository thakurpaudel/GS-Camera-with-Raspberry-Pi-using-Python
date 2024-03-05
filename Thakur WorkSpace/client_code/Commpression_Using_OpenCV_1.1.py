import io
import cv2
import numpy as np
import time
from datetime import datetime
from queue import Queue
from threading import Thread
from picamera2 import Picamera2

# Simplified compression function to improve speed
def compress_image_simple(image):
    start_time = time.time()
    # Convert image to a NumPy array
    image_np = np.frombuffer(image, dtype=np.uint8)
    image_np = cv2.imdecode(image_np, cv2.IMREAD_COLOR)
    # Perform a simple and fast compression (resize here for demonstration)
    compressed_image = cv2.resize(image_np, (int(image_np.shape[1] * 0.5), int(image_np.shape[0] * 0.5)))
    # Convert back to bytes
    _, buffer = cv2.imencode('.jpg', compressed_image)
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
    cv2.putText(original_img, f"Timestamp: {timestamp}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(original_img, f"Size: {original_size} bytes", (10, 70), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(compressed_img, f"Size: {compressed_size} bytes", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # Display images
    cv2.imshow('Original Image', original_img)
    cv2.imshow('Compressed Image', compressed_img)
    cv2.waitKey(1)

def capture_images(queue):
    picamera2 = Picamera2()
    preview_config = picamera2.create_preview_configuration()
    picamera2.configure(preview_config)
    time.sleep(1)  # Allow some time for sensor to adjust to conditions
    capture_config = picamera2.create_still_configuration()
    picamera2.configure(capture_config)
    picamera2.start()

    while True:
        image = io.BytesIO()
        picamera2.capture_file(image, format='jpeg')
        image.seek(0)
        original_image_data = image.getvalue()
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        original_size = len(original_image_data)
        queue.put((original_image_data, timestamp, original_size))

if __name__ == "__main__":
    image_queue = Queue()
    capture_thread = Thread(target=capture_images, args=(image_queue,))
    capture_thread.daemon = True
    capture_thread.start()

    try:
        while True:
            if not image_queue.empty():
                original, timestamp, original_size = image_queue.get()
                compressed = compress_image_simple(original)
                compressed_size = len(compressed)
                display_images(original, compressed, timestamp, original_size, compressed_size)
    except KeyboardInterrupt:
        print("Stopping...")
        cv2.destroyAllWindows()