from socket import socket


class DummySpectrometer:
    server_socket: socket

    def __init__(self, port: int):
        self.server_socket = socket()
        self.server_socket.bind(("", port))
        self.server_socket.listen(1)
        print("listening")
        connection, address = self.server_socket.accept()
        print("connected")
        print(connection)
        print(address)

        while True:
            message = self.server_socket.recv(1024)
            print("recieved!")
            print(message)
