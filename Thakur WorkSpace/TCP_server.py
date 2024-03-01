import socket

def connect_to_server():
    # Server address and port
    server_address = ('192.168.1.8', 12345)  # Replace <RaspberryPi_IP> with your Raspberry Pi's IP address

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the server
    sock.connect(server_address)

    try:
        # Send data
        message = 'I am thakur paudel '
        sock.sendall(message.encode('utf-8'))

        # Look for the response
        response = sock.recv(1024).decode('utf-8')
        print(f"Received: {response}")

    finally:
        # Close the socket to clean up
        sock.close()

if __name__ == "__main__":
    connect_to_server()
