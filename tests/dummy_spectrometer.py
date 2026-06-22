import asyncio
import random
from socket import socket


class DummySpectrometer:
    server_socket: socket

    version: int = 4110
    integration_time: int = 10
    last_scan_data: list[int]
    scan_data_length = 2044

    def __init__(self, port: int):
        self.server_socket = socket()
        self.server_socket.bind(("", port))
        self._randomise_scan_data()

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
                # ALSO make sure they have the \n at the end
                # Replicate the bug out if they dont
                return self.set_integration_time(0)
            case "Z":
                return self.get_last_scan()
            case "S":
                # There should be a wait in here somewhere
                # TODO: make async??
                return self.scan()
            case "?":
                match request[1]:
                    case "I":
                        return self.get_integration_time()
        return b""

    # This double mapping is BAD
    # (handle request mapping and including message in repsonse)
    # TODO: Figure out a way to get rid of it
    def get_version(self) -> bytes:
        return self.wrap_response("v", str(self.version) + " ")

    def get_integration_time(self) -> bytes:
        return self.wrap_response("?I", str(self.integration_time) + " ")

    def set_integration_time(self, integration_time: int) -> bytes:
        self.integration_time = integration_time
        return self.wrap_response("I" + str(self.integration_time) + "\n\r", " ")

    def get_last_scan(self) -> bytes:
        return self.wrap_response("Z", self._scan_string())

    def scan(self) -> bytes:
        self._randomise_scan_data()
        return self.wrap_response("S", self._scan_string(), delimeter=b"\02")

    def _scan_string(self) -> str:
        # Header of scan data
        # TODO: Add comments for what these numbers mean (in manual)
        # 5th value might be different for an actual scan vs getting last scan
        scan_string = "65535 0 1 8 0 0 0 "

        for value in self.last_scan_data:
            scan_string += str(value)
            scan_string += " "

        scan_string += "65533 "

        return scan_string

    def _randomise_scan_data(self):

        # TODO: could make this a smoother distribution but this is not important
        self.last_scan_data = []
        for _ in range(self.scan_data_length):
            self.last_scan_data.append(random.randint(900, 1200))

    @staticmethod
    def wrap_response(
        request: str,
        response: str,
        delimeter: bytes = b"\x06",
        footer: bytes = b"\n\r> ",
    ) -> bytes:
        return request.encode("ascii") + delimeter + response.encode("ascii") + footer
