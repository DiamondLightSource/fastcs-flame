import asyncio
import random
from socket import socket


class DummySpectrometer:
    server_socket: socket

    _version: int = 4110
    _integration_time: int = 10
    _last_scan_data: list[int]
    _scan_data_length = 2044
    _chunk_size: int = 1024

    def __init__(self, port: int):
        """
        Binds a socket to a port on localhost (127.0.0.1)
        port: Port to bind socket to
        """
        self.server_socket = socket()
        self.server_socket.bind(("", port))
        self._randomise_scan_data()

    async def start(self):
        """
        Starts the server listening process
        This will respond to incomming requests until a "" is sent
        """

        # Listen for 1 connection
        self.server_socket.listen(1)
        # Allows us to use async code with sockets
        self.server_socket.setblocking(False)

        loop = asyncio.get_event_loop()
        # Do we also need to setblocking for connection??
        connection, address = await loop.sock_accept(self.server_socket)
        # Send initial message like spectrometer
        # (indicates spectrometer is in ascii mode, not binary)
        connection.send(b"\xff\xfa,k\x0f\xff\xf0")

        # Recieve and process messages until the connection is closed
        while True:
            raw_last_message = await loop.sock_recv(connection, 1024)
            last_message = raw_last_message.decode("ascii")
            if last_message == "":
                return
            response = self._handle_request(last_message)
            self._respond_in_chunks(connection, response)

    def _respond_in_chunks(self, connection: socket, response: bytes):
        """
        Sends messages in evenly sized chunks
        Simulates how real spectrometer sends data
        """
        # TODO: Could add a delay to make messages more realistic

        # Keep taking chunks until the message is all sent
        while True:
            if len(response) < self._chunk_size:
                connection.send(response)
                return

            # take first chunk of the message and send it
            next_chunk = response[0 : self._chunk_size]
            response = response[self._chunk_size :]
            connection.send(next_chunk)

    def _handle_request(self, request: str) -> bytes:
        """
        Processes sent requests
        Returns response (in bytes)
        request: The request message recieved decoded as a string
        """
        # Would in be neater to have request in bytes and decode it here??
        # So then its bytes in bytes out??

        match request[0]:
            case "v":
                return self.get_version()
            case "I":
                return self.set_integration_time(request)
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
        return self.wrap_response("v", str(self._version) + " ")

    def get_integration_time(self) -> bytes:
        return self.wrap_response("?I", str(self._integration_time) + " ")

    def set_integration_time(self, request: str) -> bytes:
        if "\n" not in request:
            # TODO: make sure this is correct
            return b"\x15"
        new_integration_time = int(request[1:].split("\n")[0].rstrip())
        self._integration_time = new_integration_time
        return self.wrap_response("I" + str(self._integration_time) + "\n\r", " ")

    def get_last_scan(self) -> bytes:
        return self.wrap_response("Z", self._scan_string())

    def scan(self) -> bytes:
        """
        Conducts a new scan and returns the result of it
        """
        self._randomise_scan_data()
        return self.wrap_response("S", self._scan_string(), delimeter=b"\02")

    def _scan_string(self) -> str:
        """
        Creates the body of a scan response
        This includes scan metadata and start and finish values
        """
        # Header of scan data
        # TODO: Add comments for what these numbers mean (in manual)
        # 5th value might be different for an actual scan vs getting last scan
        scan_string = "65535 0 1 8 0 0 0 "

        for value in self._last_scan_data:
            scan_string += str(value)
            scan_string += " "

        scan_string += "65533 "

        return scan_string

    def _randomise_scan_data(self):
        """
        Replaces the existing _last_scan_data list with a new random one
        """
        # TODO: could make this a smoother distribution but this is not important
        last_last_value = self._last_scan_data[-1]
        self._last_scan_data = []
        for _ in range(self._scan_data_length):
            self._last_scan_data.append(random.randint(900, 1200))

        # Ensure that the last value is not the same as before
        # This means we can test a new scan has actually happened by comparing
        # the last value
        # Such a low probability of happening anyway
        if self._last_scan_data[-1] == last_last_value:
            self._last_scan_data[-1] += 1

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
