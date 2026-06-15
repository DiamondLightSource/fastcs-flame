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
        # send initial message like spectrometer
        # (indicates spectrometer is in ascii mode, not binary)
        connection.send(b"\xff\xfa,k\x0f\xff\xf0")

        last_message = "Blank"
        while last_message != "":
            message = await loop.sock_recv(connection, 1024)
            last_message = message.decode("ascii")
            response = self.handle_request(last_message)
            connection.send(response)
            await asyncio.sleep(1)

    def handle_request(self, request: str) -> bytes:
        match request:
            case "v":
                return self.send_version()
        return b""

    def send_version(self) -> bytes:
        return self.wrap_response("v", "4110 ")

    @staticmethod
    def wrap_response(
        request: str,
        response: str,
        delimeter: bytes = b"\x06",
        footer: bytes = b"\n\r> ",
    ) -> bytes:
        return request.encode("ascii") + delimeter + response.encode("ascii") + footer
