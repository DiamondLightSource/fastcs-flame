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
        self.socket_obj.bind((self.ip, self.port))
        # TODO: listen for initial message from device and validate??

    def _small_query(self, query: str) -> str:
        if self.socket_obj is None:
            # TODO: add handling when socket is None
            return ""

        self.socket_obj.send(query.encode("ascii"))

        raw_response = self.socket_obj.recv(self.recieve_buffer_size)
        # TODO: look for acknowledgement characters here
        response = raw_response.decode("ascii")

        return response

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
