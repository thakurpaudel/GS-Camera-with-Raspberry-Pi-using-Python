#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
from datetime import datetime
import time

# Server's hostname or IP address
SERVER_IP = '192.168.1.8'
# The port used by the server
SERVER_PORT = 8888
BUFFER_SIZE = 1024
# Timeout for the server response in seconds
SERVER_TIMEOUT = 2

def check_server_online(sock, server_address):
    """Send a ping to the server and wait for a pong."""
    try:
        sock.sendto(b'ping', server_address)
        sock.settimeout(SERVER_TIMEOUT)
        # Wait for response
        data, _ = sock.recvfrom(BUFFER_SIZE)
        if data.decode() == 'pong':
            return True
    except socket.timeout:
        print("Server response timed out")
    except Exception as e:
        print(f"An error occurred: {e}")
    return False

# Create a UDP socket at client side
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    server_address = (SERVER_IP, SERVER_PORT)
    
    while True:
        print("Checking if server is online...")
        if check_server_online(sock, server_address):
            print("Server is online. Starting to send timestamps...")
            try:
                while True:
                    # Get the current timestamp
                    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    message = f"Timestamp: {timestamp}"
                    
                    # Send data to server
                    sock.sendto(message.encode(), server_address)
                    print(f"Sent to server: {message}")

                    # Optional: Receive response from server
                    # If your server doesn't respond, you can remove this part
                    data, server = sock.recvfrom(BUFFER_SIZE)
                    print(f"Received from server: {data.decode()}")

                    # Wait for 1 second before sending the next timestamp
                    time.sleep(1)
            except KeyboardInterrupt:
                print("Program terminated by user")
                break
            except Exception as e:
                print(f"An error occurred: {e}")
        else:
            print("Server is offline or not responding. Retrying in 1 seconds...")
            time.sleep(1)