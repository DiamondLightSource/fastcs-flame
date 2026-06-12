from socket import socket


class SpectrometerTelecommunicator:
    ip: str
    port: int
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
