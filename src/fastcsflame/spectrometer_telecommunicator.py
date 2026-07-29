import asyncio
from socket import socket

from fastcs.logging import logger

# Initial message recieved from a TelNet connection
# We do NOT communicate using TelNet (we use raw IP sockets)
# BUT we still expect this message when connecting to the device
TELNET_ASCII_CONNECTION_MESSAGE = b"\xff\xfa,k\x0f\xff\xf0"


class UnexpectedResponseError(Exception):
    pass


class NotConnectedError(BaseException):
    pass


class AlreadyConnectedError(Exception):
    pass


class SpectrometerTelecommunicator:
    """
    Communicates with Flame spectrometers using raw IP sockets
    """

    ip: str
    port: int
    recieve_buffer_size: int
    timeout: float

    socket_obj: socket | None = None
    connected: bool = False

    def __init__(
        self, ip: str, port: int, recieve_buffer_size: int = 1024, timeout: float = 15.0
    ):
        """
        Creates the communicator object but does NOT connect to the spectrometers socket
        OR validate socket correctness
        To connect use connect() method
        ip: IP address of the device the spectrometer is connected to
            example: "192.168.0.1"
        port: Port of the device the spectrometer is communicating on
        recieve_buffer_size: Size of buffer (in bytes) for recieving messages
        timeout: Time to wait (in seconds) before raising an error when no response
            is recieved (whilst expecting a response)
        """
        self.ip = ip
        self.port = port
        self.recieve_buffer_size = recieve_buffer_size
        self.timeout = timeout

    async def connect(self):
        """
        Connects to the spectrometers socket
        raises
            TimeoutError
                (when the socket address is wrong
                OR the device does not send a startup message)
            UnexpectedResponseError
                (when the startup message from the spectrometer is not as expected,
                this could just mean its in binary mode)
        Unlikely errors:
            ConnectionRefusedError
            ConnectionResetError
            OSError
        """

        # TODO: Should check if socket_obj has been closed somehow
        if self.connected:
            raise AlreadyConnectedError("Connect method has already been run")

        loop = asyncio.get_event_loop()
        self.socket_obj = socket()
        self.socket_obj.setblocking(False)

        async with asyncio.timeout(self.timeout):
            await loop.sock_connect(self.socket_obj, (self.ip, self.port))

        self.connected = True

        # connection message is the initial message sent by the device when you connect
        # I'm not 100% sure what it means yet
        # But the socket needs to be cleared for the next message either way
        # Message can NOT be decoded into ascii (in binary??)
        async with asyncio.timeout(self.timeout):
            connection_message = await loop.sock_recv(
                self.socket_obj, self.recieve_buffer_size
            )

        # TODO: Add a case for binary start up message too
        # Maybe send signal to convert it ascii??
        if connection_message != TELNET_ASCII_CONNECTION_MESSAGE:
            raise UnexpectedResponseError(
                "Expected connection message: b'\\xff\\xfa,k\\x0f\\xff\\xf0' "
                + f"recieved: {connection_message}"
            )

    async def _send_query(self, query: str, end_signal: bytes = b"\n\r> ") -> bytes:
        """
        Send a query that can handle single or multiple packet responses
        query: Query to send to spectrometer (before byte encoding)
        end_signal: Any collection of bytes included in the final packet
        returns raw response
                raises
            NotConnectedError
                (when connect method hasnt been called before this method)
            TimeoutError
                (when no response was recieved from the device)
        """
        loop = asyncio.get_event_loop()

        if self.socket_obj is None:
            raise NotConnectedError(
                "Object is not connected to spectrometer, no socket exists. "
                + "Call connect() method first"
            )

        self.socket_obj.send(query.encode("ascii"))

        response_raw: bytes = b""
        last_response_raw_section: bytes = b""

        # Keep on recieving information until a response section contains the end signal
        while last_response_raw_section.rfind(end_signal) == -1:
            async with asyncio.timeout(self.timeout):
                last_response_raw_section = await loop.sock_recv(
                    self.socket_obj, self.recieve_buffer_size
                )
            response_raw += last_response_raw_section

        return response_raw

    @staticmethod
    def _extract_response(response_raw: bytes) -> str:
        """
        Extracts the main response body from the entire response bytes and decodes it
        If response body cannot be extracted entire decoded response is returned
        """

        # Splits the response on the ascii acknowledgement character (06 in hex)
        # (This assumes we get an acknowledgement)
        # The query is returned back before the acknowledgement
        # The actual response text is after the acknowledgement

        if b"\x15" in response_raw:
            logger.warning(f"Negative acknowledgement in response: {response_raw}")
            return response_raw.decode()
        elif b"\x06" in response_raw:
            response_raw_split = response_raw.split(b"\x06")
        # This is the start of text character
        # Sometimes messages are sent with this instead of an acknowledgement character
        elif b"\x02" in response_raw:
            response_raw_split = response_raw.split(b"\x02")
        else:
            logger.warning(f"No valid delimeter in response: {response_raw}")
            return response_raw.decode("ascii")
        # query_echo_raw = response_raw_split[0]
        query_response_raw = response_raw_split[1]

        response_str = query_response_raw.decode("ascii")

        # The standard trailing text for a response
        # Contains no useful information
        if response_str[-4:] != "\n\r> ":
            logger.warning(
                f"Response end not as expected: {response_str} \n"
                + "Expected '\\n\\r> ' at tail end"
            )
            return response_str

        return response_str[:-4].strip()

    async def get_version(self) -> int:
        """
        Sends a query to get the version of the spectrometer
        returns version encoded as an integer (e.g. 4.1.0 = 410)
        raises UnexpectedResponseError
        """
        version_str = self._extract_response(await self._send_query("v"))
        try:
            version_int = int(version_str)
        except ValueError as e:
            raise UnexpectedResponseError(
                f"Expected version number, recieved '{version_str}'"
            ) from e
        return version_int

    async def set_integration_time(self, integration_time: int):
        """
        Sends a query to set the integration time value of the spectrometer
        integration_time: Value to set integration time to
        """
        # Device does not respond properly to all future messages if the trailing \n
        # is not included (until a \n is sent)
        self._extract_response(
            await self._send_query("I" + str(integration_time) + "\n")
        )

    async def get_integration_time(self) -> int:
        """
        Sends a query to get the integration time value of the spectrometer
        returns integration time
        raises UnexpectedResponseError
        """
        integration_time_str = self._extract_response(await self._send_query("?I"))
        try:
            integration_time_int = int(integration_time_str)
            return integration_time_int
        except ValueError as e:
            raise UnexpectedResponseError(
                f"Expected version number, recieved '{integration_time_str}'"
            ) from e

    async def scan(self) -> list[int]:
        """
        Triggers a new scan on the spectrometer
        returns scan data
        """
        scan_result_str = self._extract_response(await self._send_query("S"))
        return self._scan_str_to_list(scan_result_str)

    async def get_last_scan(self) -> list[int]:
        """
        Sends a query to get data from the last scan the spectrometer took
        returns scan data
        """
        scan_result_str = self._extract_response(await self._send_query("Z"))
        return self._scan_str_to_list(scan_result_str)

    @staticmethod
    def _scan_str_to_list(scan_result_str: str) -> list[int]:
        """
        Converts the body of a scan request response into a list of integer values
        scan_result_str: The body of a scan request response
            (after acknowledgement character, before newline & cariage return)
        returns scan data
        raises UnexpectedResponseError
        """
        # start with scan_results
        # split on " " to separate the numbers and put them in a list
        # get rid of the first 6 numbers and last 3
        #   as this is just meta data and handshakes
        # convert each one to an integer in a string comprehension
        try:
            data = [int(s) for s in scan_result_str.split(" ")[7:-4]]
            return data
        except ValueError as e:
            raise UnexpectedResponseError from e
