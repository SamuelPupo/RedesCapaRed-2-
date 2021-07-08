from sortedcontainers.sortedset import SortedSet

from host import Host, Device, Data, icmp_, Route


class RouterPort(Host):
    def __init__(self, signal_time: int, error_detection: str, name: str, mac: str = "FFFF", ip: tuple = (0, 0, 0, 0),
                 mask: tuple = (0, 0, 0, 0), location_port: int = 0):
        super().__init__(signal_time, error_detection, name, mac, ip, mask)
        self.location_port = location_port
        self.redirect = None

    def start(self):
        return

    def write(self, string: str):
        if string.__contains__("port="):
            string = string.split("port=")
            string[1] = str(self.location_port + 1) + string[1][1:]
            string = string[0] + "port=" + string[1]
        super().write(string)

    def ignore(self, destination_ip: tuple, origen_ip: tuple, data: list):
        self.redirect = (destination_ip, origen_ip, data)

    def write_data(self, time: int, sender: str, data: list, state: str):
        sender += ", port={}".format(self.location_port + 1)
        super().write_data(time, sender, data, state)

    def packet(self, time: int, data: list, destination_ip: tuple, origen_ip: tuple = None):
        ip = self.ip
        if origen_ip is not None:
            self.ip = origen_ip
        super().packet(time, data, destination_ip, origen_ip)
        self.ip = ip

    def write_payload(self, time: int, host_ip: str, string: str):
        string = "port={}, {}".format(self.location_port + 1, string)
        super().write_payload(time, host_ip, string)

    def start_send(self, time: int, data: list, destination_mac: list = None):
        self.data.append([])
        super().start_send(time, data, destination_mac)
        self.data.pop(len(self.data) - 2)
        self.transmitting_started = time


class Router(Device):
    def __init__(self, signal_time: int, error_detection: str, name: str, ports_number: int, mac: list = None,
                 ip: list = None, mask: list = None):
        super().__init__(name, ports_number)
        if mac is None:
            mac = ["FFFF" for _ in range(ports_number)]
        elif len(mac) != ports_number:
            print("\nWRONG MAC ADDRESS")
            raise Exception
        if ip is None:
            ip = [(0, 0, 0, 0) for _ in range(ports_number)]
        elif len(ip) != ports_number:
            print("\nWRONG IP ADDRESS")
            raise Exception
        if mask is None:
            mask = [(0, 0, 0, 0) for _ in range(ports_number)]
        elif len(mask) != ports_number:
            print("\nWRONG MASK ADDRESS")
            raise Exception
        self.ports = []
        for i in range(ports_number):
            self.ports.append(RouterPort(signal_time, error_detection, name, mac[i], ip[i], mask[i], i))
        self.routes = SortedSet()
        self.start()

    def start(self):
        file = open("output/{}_data.txt".format(self.name), 'w')
        file.close()
        file = open("output/{}_payload.txt".format(self.name), 'w')
        file.close()

    def connect(self, time: int, port: int, other_device, other_port: int):
        self.ports[port].connect(time, 0, other_device, other_port)

    def disconnect(self, time: int, port: int):
        self.ports[port].disconnect(time, 0)

    def receive_bit(self, time: int, port: int, data: Data, disconnected: bool = False):
        host = self.ports[port]
        host.receive_bit(time, 0, data, disconnected)
        redirect = host.redirect
        if redirect is not None:
            destination_ip = redirect[0]
            origen_ip = redirect[1]
            data = redirect[2]
            if not self.send_packet(time, data, destination_ip, origen_ip):
                ip = host.ip
                host.ip = destination_ip
                host.destination_host_unreachable(time, origen_ip)
                host.ip = ip
            host.redirect = None

    def send_packet(self, time: int, data: list, destination_ip: tuple, origen_ip: tuple):
        for route in self.routes:
            and_ = tuple([destination_ip[i] & route.mask[i] for i in range(len(destination_ip))])
            if and_ == route.destination:
                port = self.ports[route.interface]
                if data[8:16] == icmp_:
                    port.start_send(time, port.binary_ip(destination_ip) + port.binary_ip(origen_ip) + data)
                else:
                    port.packet(time, data, destination_ip, origen_ip)
                return True
        return False

    def send(self, time: int):
        sent = False
        for port in range(len(self.ports)):
            data = self.ports[port].send(time)
            if data != Data.NULL:
                sent = True
        return sent

    def set_mac(self, interface: int, mac: str):
        if interface < 0 or interface >= self.ports_number:
            print("\nWRONG MAC INTERFACE.")
            raise Exception
        if mac == "FFFF":
            print("\nWRONG MAC ADDRESS.")
            raise Exception
        self.ports[interface].set_mac(0, mac)

    def set_ip(self, time: int, interface: int, ip: tuple, mask: tuple):
        if interface < 0 or interface >= self.ports_number:
            print("\nWRONG IP INTERFACE.")
            raise Exception
        if ip[2] == 0 or ip[2] == 255 or ip[3] == 0 or ip[3] == 255:
            print("\nWRONG IP ADDRESS.")
            raise Exception
        self.ports[interface].set_ip(time, 0, ip, mask)

    def echo_request(self, time: int, interface: int, destination_ip: tuple):
        if interface < 0 or interface >= self.ports_number:
            print("\nWRONG PING INTERFACE.")
            raise Exception
        self.ports[interface].echo_request(time, 0, destination_ip)

    def routes_add(self, route: Route):
        self.routes.add(route)
        self.ports[route.interface].routes_add(route)

    def routes_delete(self, route: Route):
        self.routes.remove(route)
        self.ports[route.interface].routes_delete(route)

    def routes_reset(self):
        self.routes.clear()
        for port in self.ports:
            port.routes_reset()
