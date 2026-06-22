import asyncio
from socket import socket


class DummySpectrometer:
    server_socket: socket

    version: int = 4110
    integration_time: int = 10
    # Length 2044
    last_scan_data: list[int]

    def __init__(self, port: int):
        self.server_socket = socket()
        self.server_socket.bind(("", port))

    async def start(self):
        self.server_socket.listen(1)
        # Allows us to use async code with sockets
        self.server_socket.setblocking(False)

        loop = asyncio.get_event_loop()
        # Do we also need to setblocking for connection??
        connection, address = await loop.sock_accept(self.server_socket)
        # Send initial message like spectrometer
        # (indicates spectrometer is in ascii mode, not binary)
        connection.send(b"\xff\xfa,k\x0f\xff\xf0")

        last_message: str | None = None
        # Recieve and process messages until the connection is closed
        while last_message != "":
            raw_last_message = await loop.sock_recv(connection, 1024)
            last_message = raw_last_message.decode("ascii")
            response = self.handle_request(last_message)
            connection.send(response)

    def handle_request(self, request: str) -> bytes:
        match request[0]:
            case "v":
                return self.get_version()
            case "I":
                # find argument here and pass into method
                return self.set_integration_time(0)
            case "Z":
                return self.get_last_scan()
            case "S":
                return self.scan()
            case "?":
                match request[1]:
                    case "I":
                        return self.get_integration_time()
        return b""

    def get_version(self) -> bytes:
        return self.wrap_response("v", str(self.version) + " ")

    def get_integration_time(self) -> bytes:
        return b""

    def set_integration_time(self, integration_time: int) -> bytes:
        return b""

    def get_last_scan(self) -> bytes:
        return b""

    def scan(self) -> bytes:
        return b""

    @staticmethod
    def wrap_response(
        request: str,
        response: str,
        delimeter: bytes = b"\x06",
        footer: bytes = b"\n\r> ",
    ) -> bytes:
        return request.encode("ascii") + delimeter + response.encode("ascii") + footer
