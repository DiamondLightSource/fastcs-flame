from socket import socket


class UnexpectedResponseError(Exception):
    pass


class NotConnectedError(BaseException):
    pass


class SpectrometerTelecommunicator:
    """
    Communicates with Flame spectrometers using Telnet
    """

    ip: str
    port: int
    recieve_buffer_size: int = 1024
    socket_obj: socket | None = None

    def __init__(self, ip: str, port: int):
        """
        Creates the communicator object but does NOT connect to the spectrometers socket
        OR validate socket correctness
        To connect use connect() method
        ip: IP address of the device the spectrometer is connected to
            example: "192.168.0.1"
        port: Port of the device the spectrometer is communicating on
        """
        self.ip = ip
        self.port = port

    def connect(self):
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
            OSError
        """
        self.socket_obj = socket()
        self.socket_obj.connect((self.ip, self.port))

        # connection message is the initial message sent by the device when you connect
        # I'm not 100% sure what it means yet
        # But the socket needs to be cleared for the next message either way
        # Message can NOT be decoded into ascii (in binary??)
        connection_message = self.socket_obj.recv(self.recieve_buffer_size)

        # TODO: Add a case for binary start up message too
        # Maybe send signal to convert it ascii??
        if connection_message != b"\xff\xfa,k\x0f\xff\xf0":
            raise UnexpectedResponseError(
                "Expected connection message: b'\\xff\\xfa,k\\x0f\\xff\\xf0' "
                + f"recieved: {connection_message}"
            )

    def _small_query(self, query: str) -> str:
        """
        Send a query that expects a one packet response
        query: Query to send to spectrometer (before byte encoding)
        returns response body decoded
        raises
            NotConnectedError
                (when connect method hasnt been called before this method)
            TimeoutError
                (when no response was recieved from the device)
        """
        if self.socket_obj is None:
            raise NotConnectedError(
                "Object is not connected to spectrometer, no socket exists. "
                + "Call connect() method first"
            )

        self.socket_obj.send(query.encode("ascii"))

        response_raw = self.socket_obj.recv(self.recieve_buffer_size)

        return self._extract_response(response_raw)

    def _big_query(self, query: str, end_signal: bytes = b"65533") -> str:
        """
        Send a query that expects more than one packet as a response
        query: Query to send to spectrometer (before byte encoding)
        end_signal: Any collection of bytes included in the final packet
        returns response body decoded
                raises
            NotConnectedError
                (when connect method hasnt been called before this method)
            TimeoutError
                (when no response was recieved from the device)
        """
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
            last_response_raw_section = self.socket_obj.recv(self.recieve_buffer_size)
            response_raw += last_response_raw_section

        return self._extract_response(response_raw)

    @staticmethod
    def _extract_response(response_raw: bytes) -> str:
        """
        Extracts the main response body from the entire response bytes and decodes it
        """

        # Splits the response on the ascii acknowledgement character (06 in hex)
        # (This assumes we get an acknowledgement)
        # The query is returned back before the acknowledgement
        # The actual response text is after the acknowledgement
        # TODO: Check for invalid responses
        # (no ack, query not echoed correctly, invalid end characters)
        if b"\x06" in response_raw:
            response_raw_split = response_raw.split(b"\x06")
        elif b"\x02" in response_raw:
            response_raw_split = response_raw.split(b"\x02")
        else:
            print("No valid delimeter in response")
            return response_raw.decode("ascii")
        # query_echo_raw = response_raw_split[0]
        query_response_raw = response_raw_split[1]

        response_str = query_response_raw.decode("ascii")

        # The standard trailing text for a response
        # Contains no useful information
        if response_str[-4:] != "\n\r> ":
            print("response end not as expected")
            return response_str

        return response_str[:-4].strip()

    def get_version(self) -> int:
        """
        Sends a query to get the version of the spectrometer
        returns version encoded as an integer (e.g. 4.1.0 = 410)
        """
        version_str = self._small_query("v")
        version_int = int(version_str)
        return version_int

    def set_integration_time(self, integration_time: int):
        """
        Sends a query to set the integration time value of the spectrometer
        integration_time: Value to set integration time to
        """
        self._small_query("I" + str(integration_time) + "\n")

    def get_integration_time(self) -> int:
        """
        Sends a query to get the integration time value of the spectrometer
        returns integration time
        """
        integration_time_str = self._small_query("?I")
        integration_time_int = int(integration_time_str)
        return integration_time_int

    def scan(self) -> list[int]:
        """
        Triggers a new scan on the spectrometer
        returns scan data
        """
        scan_result_str = self._big_query("S")
        return self._scan_str_to_list(scan_result_str)

    def get_last_scan(self) -> list[int]:
        """
        Sends a query to get data from the last scan the spectrometer took
        returns scan data
        """
        scan_result_str = self._big_query("Z")
        return self._scan_str_to_list(scan_result_str)

    @staticmethod
    def _scan_str_to_list(scan_result_str: str) -> list[int]:
        """
        Converts the body of a scan request response into a list of integer values
        scan_result_str: The body of a scan request response
            (after acknowledgement character, before newline & cariage return)
        returns scan data
        """
        # start with scan_results
        # split on " " to separate the numbers and put them in a list
        # get rid of the first 6 numbers and last 3
        #   as this is just meta data and handshakes
        # convert each one to an integer in a string comprehension
        data = [int(s) for s in scan_result_str.split(" ")[7:-4]]
        return data
