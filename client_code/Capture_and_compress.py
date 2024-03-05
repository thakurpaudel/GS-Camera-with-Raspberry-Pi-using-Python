import io
import time
from datetime import datetime
from subprocess import Popen, PIPE
from queue import Queue
from threading import Thread
from picamera2 import Picamera2  # Assuming this is your custom class for PiCamera
from picamera2.controls import Controls

last_capture_time = time.time()
captured_frames = 0
compressed_frames = 0
total_compression_time = 0

def compress_images(images):
    global compressed_frames, total_compression_time

    # Compress a batch of images using ffmpeg
    compressed_images = []

    start_time = time.time()
    for image in images:
        # Print size of original image
        original_size = len(image)
        print("Size of original image:", original_size, "bytes")
        
        # Compress the image using ffmpeg
        #p = Popen(['ffmpeg', '-y', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23', '-f', 'image2pipe', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        
        p = Popen(['ffmpeg', '-y', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-r', '24', '-i', '-', '-q:v', '31', '-f', 'image2pipe', '-'], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.stdin.write(image)
        p.stdin.close()
        compressed_image = p.stdout.read()
        p.stdout.close()
        
        # Print size of compressed image
        compressed_size = len(compressed_image)
        print("Size of compressed image:", compressed_size, "bytes")
        
        # Calculate and print compression ratio
        compression_ratio = original_size / compressed_size
        print("Compression ratio:", compression_ratio)
        
        compressed_images.append(compressed_image)
        compressed_frames += 1

    end_time = time.time()
    total_compression_time += end_time - start_time

    return compressed_images
def capture_images(queue):
    global last_capture_time, captured_frames

    # Create a Picamera2 object
    picamera2 = Picamera2()

    # Configure camera settings
    capture_config = picamera2.create_still_configuration(buffer_count=10)
    capture_config["main"]["size"] = (1280, 720)
    picamera2.set_controls({'ExposureTime': 1})
    picamera2.set_controls({'FrameRate': 60})  # Set frame rate to 30 FPS
    picamera2.configure(capture_config)
    with picamera2.controls as ctrl:
        ctrl.AnalogueGain = 0.6
        ctrl.ExposureTime = 30000
    ctrls = Controls(picamera2)
    picamera2.start()
    time.sleep(2)

    while True:
        images = []
        for _ in range(10):  # Capture a batch of 10 images
            image = io.BytesIO()
            picamera2.capture_file(image, format='jpeg')
            image.seek(0)
            images.append(image.getvalue())

        compressed_images = compress_images(images)
        timestamp = datetime.now()
        queue.put((compressed_images, timestamp))

        # Calculate FPS for capture
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
    capture_thread.start()

    # Main thread can process captured and compressed images from the queue
    while True:
        compressed_images, timestamp = image_queue.get()
        print("Compressed images:", len(compressed_images))
        
        # Process compressed images as needed
        
        # Calculate overall FPS after compressing all images
        overall_fps = compressed_frames / total_compression_time
        print(f"Overall FPS after compression: {overall_fps:.2f}")