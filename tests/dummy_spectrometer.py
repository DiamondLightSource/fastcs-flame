import asyncio
from socket import socket


class DummySpectrometer:
    server_socket: socket

    def __init__(self, port: int):
        self.server_socket = socket()
        self.server_socket.bind(("", port))

    async def start(self):
        self.server_socket.listen(1)
        self.server_socket.setblocking(False)

        loop = asyncio.get_event_loop()
        connection, address = await loop.sock_accept(self.server_socket)

        while True:
            message = await loop.sock_recv(connection, 1024)
            print(message)
