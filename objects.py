from enum import Enum


class Instruction:
    def __init__(self, time: int, command: str, details: list):
        self.time = time
        self.command = command
        self.details = details


class Data(Enum):
    NULL = 0
    ZERO = 1
    ONE = 2


class Cable:
    def __init__(self, device=None, port: int = -1):
        self.device = device
        self.port = port
        self.data = Data.NULL

    def update(self, device=None, port: int = -1):
        self.device = device
        self.port = port


class Detection(Enum):
    CRC = 0
    HAMMING = 1


class Route:
    def __init__(self, destination: tuple, mask: tuple, gateway: tuple, interface: int):
        self.destination = destination
        self.mask = mask
        self.gateway = gateway
        self.interface = interface

    def __lt__(self, other):
        return self.mask > other.mask

    def __eq__(self, other):
        return type(other) == Route and self.destination == other.destination and self.mask == other.mask and \
               self.gateway == other.gateway and self.interface == other.interface

    def __hash__(self):
        return hash(self.mask)
