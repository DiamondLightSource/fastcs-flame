import asyncio
import random
from socket import socket


class DummySpectrometer:
    server_socket: socket

    version: int = 4110
    integration_time: int = 10
    last_scan_data: list[int]
    scan_data_length = 2044
    chunk_size: int = 1024

    def __init__(self, port: int, bind=True, pipe=None):
        """
        Binds a socket to a port on localhost (127.0.0.1)
        port: Port to bind socket to
        """
        if bind:
            self.server_socket = socket()
            self.server_socket.bind(("", port))
        self.last_scan_data = []
        self.randomise_scan_data()

        self.pipe = None
        if pipe is not None:
            self.pipe = pipe

    def pipe_message(self, message: str):
        if self.pipe is None:
            return
        self.pipe.send(message)

    async def run(self, startup_message: bytes = b"\xff\xfa,k\x0f\xff\xf0"):
        """
        Starts the server listening process
        This will respond to incomming requests until a "" is sent
        """

        # Listen for 1 connection
        self.server_socket.listen(1)
        # Allows us to use async code with sockets
        self.server_socket.setblocking(False)

        self.pipe_message("accepting")

        loop = asyncio.get_event_loop()
        # Do we also need to setblocking for connection??
        self.connection, address = await loop.sock_accept(self.server_socket)
        # Send initial message like spectrometer
        # (indicates spectrometer is in ascii mode, not binary)
        self.connection.send(startup_message)

        # Recieve and process messages until the connection is closed
        while True:
            raw_last_message = await loop.sock_recv(self.connection, 1024)
            if raw_last_message.decode("ascii") == "":
                return
            response = await self._handle_request(raw_last_message)
            self._respond_in_chunks(self.connection, response)

    def _respond_in_chunks(self, connection: socket, response: bytes):
        """
        Sends messages in evenly sized chunks
        Simulates how real spectrometer sends data
        """

        # Keep taking chunks until the message is all sent
        while True:
            if len(response) < self.chunk_size:
                connection.send(response)
                return

            # take first chunk of the message and send it
            next_chunk = response[0 : self.chunk_size]
            response = response[self.chunk_size :]
            connection.send(next_chunk)

    async def _handle_request(self, raw_request: bytes) -> bytes:
        """
        Processes sent requests
        Returns response (in bytes)
        request: The request message recieved decoded as a string
        """
        request = raw_request.decode("ascii")
        response_body: str = ""
        response_delimeter: bytes = b"\x06"

        match request[0]:
            case "v":
                response_body = self.handle_get_version_request()
            case "I":
                response_body = self.handle_set_integration_time_request(request)
            case "Z":
                response_body = await self.handle_get_last_scan_request()
            case "S":
                response_body = await self.handle_scan_request()
                response_delimeter = b"\02"
            case "?":
                match request[1]:
                    case "I":
                        response_body = self.handle_get_integration_time_request()
        if response_body == "":
            response_delimeter = b"\x15"

        return self.wrap_response(request, response_body, delimeter=response_delimeter)

    def handle_get_version_request(self) -> str:
        return str(self.version) + " "

    def handle_get_integration_time_request(self) -> str:
        return str(self.integration_time) + " "

    def handle_set_integration_time_request(self, request: str) -> str:
        if "\n" not in request:
            # TODO: make sure this is correct
            return ""
        new_integration_time = int(request[1:].split("\n")[0].rstrip())
        self.integration_time = new_integration_time
        return " "

    async def handle_get_last_scan_request(self) -> str:
        await asyncio.sleep(8)
        return self._scan_string()

    async def handle_scan_request(self) -> str:
        """
        Conducts a new scan and returns the result of it
        """
        await asyncio.sleep(11)
        self.randomise_scan_data()
        return self._scan_string()

    def _scan_string(self) -> str:
        """
        Creates the body of a scan response
        This includes scan metadata and start and finish values
        """
        # Header of scan data
        # TODO: Add comments for what these numbers mean (in manual)
        # 5th value might be different for an actual scan vs getting last scan
        scan_string = "65535 0 1 8 0 0 0 "

        for value in self.last_scan_data:
            scan_string += str(value)
            scan_string += " "

        scan_string += "65533 "

        return scan_string

    def randomise_scan_data(self):
        """
        Replaces the existing _last_scan_data list with a new random one
        """
        # TODO: could make this a smoother distribution but this is not important
        last_last_value = 0
        if self.last_scan_data != []:
            last_last_value = self.last_scan_data[-1]
        self.last_scan_data = []
        for _ in range(self.scan_data_length):
            self.last_scan_data.append(random.randint(900, 1200))

        # Ensure that the last value is not the same as before
        # This guarantees the two scans will not be the same
        # And also allows us to be lazy and only check the last value for scan changes
        # Such a low probability of happening anyway
        if self.last_scan_data[-1] == last_last_value:
            self.last_scan_data[-1] += 1

    @staticmethod
    def wrap_response(
        request: str,
        response: str,
        delimeter: bytes = b"\x06",
        footer: bytes = b"\n\r> ",
    ) -> bytes:
        """
        Packages responses
        """
        return request.encode("ascii") + delimeter + response.encode("ascii") + footer
