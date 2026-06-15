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
        # Do we also need to setblocking for connection??
        connection, address = await loop.sock_accept(self.server_socket)

        last_message = "Blank"
        while last_message != "":
            message = await loop.sock_recv(connection, 1024)
            last_message = message.decode("ascii")
            print(last_message)
            await asyncio.sleep(1)
