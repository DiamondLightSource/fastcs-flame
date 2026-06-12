from socket import socket


class SpectrometerTelecommunicator:
    ip: str
    port: int
    recieve_buffer_size: int = 1024
    socket_obj: socket | None = None

    def __init__(self, ip: str, port: int):
        # TODO: add ip checking
        # Also add conversion from domain to IP??
        self.ip = ip
        self.port = port

    def connect(self):
        # TODO: add error handling here
        self.socket_obj = socket()
        self.socket_obj.connect((self.ip, self.port))

        # connection message is the initial message sent by the device when you connect
        # I'm not 100% sure what it means yet
        # But the socket needs to be cleared for the next message either way
        # Message can NOT be decoded into ascii (in binary??)
        connection_message = self.socket_obj.recv(self.recieve_buffer_size)

        if connection_message != b"\xff\xfa,k\x0f\xff\xf0":
            # TODO: add proper error handling here
            print("connection message not what was expected: ")
            print(connection_message)

    def _small_query(self, query: str) -> str:
        if self.socket_obj is None:
            # TODO: add handling when socket is None
            return ""

        self.socket_obj.send(query.encode("ascii"))

        response_raw = self.socket_obj.recv(self.recieve_buffer_size)

        # Splits the response on the ascii acknowledgement character (06 in hex)
        # (This assumes we get an acknowledgement)
        # The query is returned back before the acknowledgement
        # The actual response text is after the acknowledgement
        # TODO: Check for invalid responses
        # (no ack, query not echoed correctly, invalid end characters)
        response_raw_split = response_raw.split(b"\06")
        # query_echo_raw = response_raw_split[0]
        query_response_raw = response_raw_split[1]

        response_str = query_response_raw.decode("ascii")

        # The standard trailing text for a response
        # Contains no useful information
        if response_str[-5:] != " \n\r> ":
            print("response end not as expected")
            return response_str

        return response_str[:-5]

    def _big_query(self, query: str, end_string="65533") -> str:
        if self.socket_obj is None:
            # TODO: add handling when socket is None
            return ""

        self.socket_obj.send(query.encode("ascii"))

        response = ""
        while end_string not in response:
            raw_response = self.socket_obj.recv(self.recieve_buffer_size)
            response.join(raw_response.decode("ascii"))
        # TODO: Add a failsafe incase transmission is stopped half way through
        # TODO: look for acknowledgement characters here
        return response

    def get_version(self) -> int:
        version_str = self._small_query("v")
        version_int = int(version_str)
        return version_int

    def set_integration_time(self, integration_time: int):
        self._small_query("I" + str(integration_time))

    def get_integration_time(self) -> int:
        integration_time_str = self._small_query("?I")
        integration_time_int = int(integration_time_str)
        return integration_time_int

    def scan(self) -> list[int]:
        scan_result_str = self._big_query("S")
        return self._scan_str_to_list(scan_result_str)

    def get_last_scan(self) -> list[int]:
        scan_result_str = self._big_query("Z")
        return self._scan_str_to_list(scan_result_str)

    @staticmethod
    def _scan_str_to_list(scan_result_str: str) -> list[int]:
        # start with scan_results
        # split on " " to separate the numbers and put them in a list
        # get rid of the first 6 numbers and last 3
        #   as this is just meta data and handshakes
        # convert each one to an integer in a string comprehension
        data = [int(s) for s in scan_result_str.split(" ")[7:-4]]
        return data
