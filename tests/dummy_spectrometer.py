import asyncio
import random
from socket import socket

TELNET_STARTUP_MESSAGE = b"\xff\xfa,k\x0f\xff\xf0"


class DummySpectrometer:
    server_socket: socket

    version: int = 4110
    integration_time: int = 10
    last_scan_data: list[int]
    scan_data_length = 2044
    chunk_size: int = 1024
    connected: bool

    disconnect_after_time: int | None
    reconnect_after_time: int | None

    waiting_for_connection: asyncio.Event

    def __init__(
        self,
        port: int,
        bind=True,
        disconnect_after_time: int | None = None,
        reconnect_after_time: int | None = None,
    ):
        """
        Binds a socket to a port on localhost (127.0.0.1)
        port: Port to bind socket to
        """
        if bind:
            self.server_socket = socket()
            self.server_socket.bind(("", port))
        self.last_scan_data = []
        self.randomise_scan_data()

        self.connected = False
        self.connection = None

        self.disconnect_after_time = disconnect_after_time
        self.reconnect_after_time = reconnect_after_time

        self.waiting_for_connection = asyncio.Event()

    async def run(
        self,
    ):
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

        self.waiting_for_connection.set()

        self.connection, address = await loop.sock_accept(self.server_socket)
        self.waiting_for_connection.clear()
        self.connected = True
        # Send initial message like spectrometer
        # (indicates spectrometer is in ascii mode, not binary)
        self.connection.send(TELNET_STARTUP_MESSAGE)

        # Start ephemeral process
        # asyncio.create_task(self.ephemeral_process())

        # Recieve and process messages until the connection is closed
        while self.connected:
            raw_last_message = await loop.sock_recv(self.connection, 1024)
            if raw_last_message.decode("ascii") == "":
                await self.disconnect()
                return
            response = await self._handle_request(raw_last_message)
            self._respond_in_chunks(self.connection, response)

    async def disconnect(self):
        if self.connection is None:
            return
        self.connection.close()
        self.connection = None
        self.server_socket.close()
        # This method is quite crude but it seems to have a high success rate
        # Ideally you would run recv from the socket until a b'' is recieved
        # This would also require a timeout incase nothing is ever recieved
        # And im not sure what you would even do in this case when you already
        # tried to close it??
        await asyncio.sleep(3)

    async def ephemeral_process(self):
        if self.disconnect_after_time is not None:
            await asyncio.sleep(self.disconnect_after_time)
        await self.disconnect()
        if self.reconnect_after_time is not None:
            await asyncio.sleep(self.reconnect_after_time)
            self.disconnect_after_time = None
            self.reconnect_after_time = None
            await self.run()

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
