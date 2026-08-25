import asyncio
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager, contextmanager
from decimal import Decimal
from socket import socket

from fastcs.logging import logger

# Initial message recieved from a TelNet connection
# We do NOT communicate using TelNet (we use raw IP sockets)
# BUT we still expect this message when connecting to the device
# This message is independant of whether the device is in ascii or binary mode
TELNET_CONNECTION_MESSAGE = b"\xff\xfa,k\x0f\xff\xf0"


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

    socket_obj: socket
    connected: bool
    on_connected_change: Callable[[bool], Coroutine[None, None, None]] | None
    on_connected_task: asyncio.Task

    # Used to prevent simulatneous messages to the device
    message_lock: asyncio.Lock

    # A reference to the task that listens for an interruption in connection
    # If a reference to running tasks is not kept they can be garbage collected
    # Should only be None if connected is False
    disconnect_listen_task: asyncio.Task | None

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
        self.connected = False
        self.on_connected_change = None
        self.disconnect_listen_task = None

        self.message_lock = asyncio.Lock()

    async def set_connected(self, value: bool):
        self.connected = value
        if self.on_connected_change is not None:
            self.on_connected_task = asyncio.create_task(
                self.on_connected_change(value)
            )

    async def connect(self):
        """
        Starts communications to the spectrometer
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

        Connects to the spectrometers socket, listens and parses its initial message
        and starts the task that listens for an interruption in the connection
        """

        try:
            await self._connect_socket()
            await self._listen_for_connection_message()
        except BaseException as e:
            if hasattr(self, "socket_obj"):
                self.socket_obj.close()
            raise e

        await self.set_connected(True)

        await self._set_ascii_mode()

        if self.disconnect_listen_task is None:
            self.disconnect_listen_task = asyncio.create_task(
                self._listen_for_disconnection()
            )

    async def _connect_socket(self):
        """
        Establishes a connection with the device
        Do NOT run this method without listening for the intial
        connection message from the spectrometer after
        raises:
            AlreadyConnectedError
                If this objects is already connected to the spectrometer
            TimeoutError
                If connection attempt times out
                This is likely because something is already connected to
                the device's port
        """
        # TODO: Should check if socket_obj has been closed somehow
        if self.connected:
            raise AlreadyConnectedError("Connect method has already been run")

        loop = asyncio.get_event_loop()
        self.socket_obj = socket()
        self.socket_obj.setblocking(False)

        async with asyncio.timeout(self.timeout):
            await loop.sock_connect(self.socket_obj, (self.ip, self.port))

    async def _listen_for_connection_message(self):
        """
        Listens for the innitial connection message from the spectrometer
        raises:
            TimeoutError
                When the device takes too long to send its initial connection message
        Logs a warning when the initial connection message was not what it expected
        """
        loop = asyncio.get_event_loop()
        # connection message is the initial message sent by the device when you connect
        # I'm not 100% sure what it means yet
        # But the socket needs to be cleared for the next message either way
        # Message can NOT be decoded into ascii (in binary??)
        async with asyncio.timeout(self.timeout):
            connection_message = await loop.sock_recv(
                self.socket_obj, self.recieve_buffer_size
            )

        if connection_message != TELNET_CONNECTION_MESSAGE:
            logger.warning(
                "Unexpected connection message recieved: "
                + f"Expected connection message: {TELNET_CONNECTION_MESSAGE} "
                + f"recieved: {connection_message}"
            )

    async def _set_ascii_mode(self):
        """
        Converts spectrometer to ascii communication mode if its not already using it
            raises
                ValueError OR UnexpectedResponseError
                    (when mode query doesnt respond as expected)
                AssertionError
                    (when conversion response is not as expected)
        """

        # Query mode
        response_raw = await self._send_query("?B")

        # Binary responses to query mode take up 3 bytes exactly
        # Means the response is not in binary
        if len(response_raw) != 3:
            binary_mode_value = int(self._extract_response(response_raw))
            if binary_mode_value != 0:
                raise UnexpectedResponseError(
                    "Device gave unexpected response to communication mode query "
                    + "expected: 1 "
                    + f"recieved: {binary_mode_value}"
                )
            # Were in ascii mode and the binary mode query returned false
            return

        # First bit should be acknowledgement
        if response_raw[0] != b"\x06":
            raise UnexpectedResponseError(
                "No acknowledgement recieved from mode query "
                + "expected: \x06\x00\x01"
                + f"recieved: {response_raw}"
            )

        # Convert to ascii mode
        ascii_mode_response = self._extract_response(await self._send_query("aA"))
        assert ascii_mode_response == ""

    async def _listen_for_disconnection(self):
        """
        Constantly listens for a disconnection message from the device

        This will be an empty bytes array (b"")
        This method will not end so its recommended to run as a task
        If this method is run as a task the field disconnect_listen_task
        should be set to its task reference
        This object will not be able to recieve messages from the device
        whilst this task is running
        """
        if not self.connected:
            return
        loop = asyncio.get_event_loop()
        # NOTE: If you get an OSError here its most likely because you closed the
        # server socket as soon as it opened
        message = await loop.sock_recv(self.socket_obj, self.recieve_buffer_size)
        if message == b"":
            await self.disconnect(cancel_disconnect_task=False)
        else:
            print(f"Unexpected message from device: {message}")

    @contextmanager
    def pause_disconnect_listening(self):
        """
        A context manager to temporarily pause the disconnect listening task

        This should be used whilst sending messages that expect a response
        """
        # Raise an exception if its None??
        if self.disconnect_listen_task is not None:
            self.disconnect_listen_task.cancel()
            self.disconnect_listen_task = None

        yield

        self.disconnect_listen_task = asyncio.create_task(
            self._listen_for_disconnection()
        )

    @asynccontextmanager
    async def message_lock_manager(self):
        """
        A context manager that acquires the message lock

        This should be used whilst sending messages that expect a response
        The lock will be released automatically when the context is left
        """

        await self.message_lock.acquire()

        yield

        self.message_lock.release()

    async def disconnect(self, cancel_disconnect_task=True):
        """
        Closes the connection with the spectrometer
        cancel_disconnect_task: Whether to cancel the disconnect task
            inside this method or not
            There is only one scenario where this should be False, that
            is when this method is being called from the disconnect task
        """
        if not self.connected:
            return
        if self.disconnect_listen_task is not None and cancel_disconnect_task:
            self.disconnect_listen_task.cancel()
        await self.set_connected(False)
        self.socket_obj.close()
        # This method is quite crude but it seems to have a high success rate
        # Ideally you would run recv from the socket until a b'' is recieved
        # This would also require a timeout incase nothing is ever recieved
        # And im not sure what you would even do in this case when you already
        # tried to close it??
        await asyncio.sleep(0.5)

    async def restart_connection(self):
        """
        Restarts the device connection

        Just calls disconnect and then connect
        """
        await self.disconnect()
        await self.connect()

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
        if not self.connected:
            raise NotConnectedError(
                "Object is not connected to spectrometer, no socket exists. "
                + "Call connect() method first"
            )

        async with self.message_lock_manager():
            with self.pause_disconnect_listening():
                # Double check connection is still up after waiting for lock
                if self.connected:
                    self.socket_obj.send(query.encode("ascii"))

                    response_raw = await self._listen_for_response(
                        end_signal=end_signal
                    )
                else:
                    response_raw = b""

        # Means connection was broken at some point
        if response_raw == b"":
            # Try restarting connection
            # This will throw an error if the connection is still down
            await self.restart_connection()
            # Try sending query again
            # Could cause a recursive loop in a very unlikely case
            # Connecting works but response is always like a disconnected socket
            return await self._send_query(query, end_signal=end_signal)

        return response_raw

    async def _listen_for_response(
        self, end_signal: bytes = b"\n\r> ", maximum_messages: int = 1000
    ):
        """
        Listens for a message from the spectrometer
        end_signal: Array of bytes to look for to know the message has ended
        maximum_messages: How many message chunks to listen out for before
            stopping listening

        Listens for message chunks until a chunk contains the end signal
        Returns all chunks appended
        """
        # Disconnect listen task should alays be cancelled before running this method
        # Cant do it inside the method as it may be too late
        if self.disconnect_listen_task is not None:
            print("raise exception")

        loop = asyncio.get_event_loop()
        if not self.connected:
            return b""

        response_raw: bytes = b""
        last_response_raw_section: bytes = b""

        # Keep on recieving information until a response section contains the end signal
        for _ in range(maximum_messages):
            async with asyncio.timeout(self.timeout):
                last_response_raw_section = await loop.sock_recv(
                    self.socket_obj, self.recieve_buffer_size
                )
            # Means connection has been broken
            if last_response_raw_section == b"":
                break
            response_raw += last_response_raw_section
            if last_response_raw_section.rfind(end_signal) != -1:
                return response_raw

        print("maximum message length exceeded")
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
        try:
            return self._scan_str_to_list(scan_result_str)
        except ValueError as e:
            raise UnexpectedResponseError from e

    async def get_last_scan(self) -> list[int]:
        """
        Sends a query to get data from the last scan the spectrometer took
        returns scan data
        """
        scan_result_str = self._extract_response(await self._send_query("Z"))
        try:
            return self._scan_str_to_list(scan_result_str)
        except ValueError as e:
            raise UnexpectedResponseError from e

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
        # get rid of the first 7 numbers and last 1
        #   as this is just meta data and handshakes
        # convert each one to an integer in a string comprehension
        if len(scan_result_str.split(" ")) < 8:
            raise ValueError
        data = [int(s) for s in scan_result_str.split(" ")[7:-1]]
        print(data)
        return data

    async def set_lamp(self, on: bool):
        # Copied from integration time code
        # Needs manual testing
        lamp_value = 0
        if on:
            lamp_value = 1
        self._extract_response(await self._send_query("J" + str(lamp_value) + "\n"))

    async def get_wcc(self, order: int) -> float:
        response = self._extract_response(
            await self._send_query("?x" + str(order + 1) + "\n")
        )

        try:
            return float(response)
        except ValueError as e:
            raise UnexpectedResponseError from e

    async def set_wcc(self, order: int, value: float):
        value_str = self._float_to_str14(value)

        # Need to insert a character in the second space of the value string
        # This character gets ignored when sending to spectrometer for some reason
        underscore_value_str = value_str[:1] + "_" + value_str[1:]
        query = f"x{order + 1}\r{underscore_value_str}\n"
        # Cant extract response as it doesnt follow the same format as the others
        # Doesnt include an acknowledgement bit as almost any input is valid
        response_raw = await self._send_query(query)
        if b"\x15" in response_raw:
            logger.warning("Negative acknowledgement recieved for wcc set")
        if value_str not in response_raw.decode():
            raise UnexpectedResponseError

    @staticmethod
    def _float_to_str14(value: float) -> str:
        scientific_notation_str = f"{Decimal(value):.7e}"
        length = len(scientific_notation_str)
        # Format of scientific notation:
        # (-)X.XXXXXXXe(+/-)(X)X
        #             ^ exponent index
        # Goal format:
        # (-)X.XXXXXXXe(-)XX
        exponent_index = scientific_notation_str.find("e")
        # Exponent must be made up of 2 digits
        # Python Decimal cannot do this for us
        # If e[sign][exponent] takes up 3 digits [exponent] only takes up 1
        if length - exponent_index == 3:
            # Insert extra 0
            scientific_notation_str = (
                scientific_notation_str[: exponent_index + 2]
                + "0"
                + scientific_notation_str[exponent_index + 2 :]
            )
        # Decimal notation can include a + before the exponent value
        # We do not want this
        plus_index = scientific_notation_str.find("+")
        if plus_index != -1:
            # Remove +
            scientific_notation_str = (
                scientific_notation_str[:plus_index]
                + scientific_notation_str[plus_index + 1 :]
            )
        return scientific_notation_str
