import logging
import os
import plistlib
import socket
import struct
import typing
import weakref
from typing import Any, Union

from .exceptions import SocketError, MuxReplyError
from .utils import set_socket_timeout

PROGRAM_NAME = "SSHCmd"
logger = logging.getLogger(__name__)


def _get_available_port():
    with socket.socket() as s:
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()
    return port


def create_socket(addr: Union[str, typing.Tuple[str, int], socket.socket, Any]):
    if isinstance(addr, socket.socket):
        return addr
    else:
        if isinstance(addr, str):
            if ':' in addr:
                host, port = addr.split(":", 1)
                addr = (host, int(port))
                family = socket.AF_INET
            elif os.path.exists(addr):
                family = socket.AF_UNIX
            else:
                raise SocketError("socket unix:{} unable to connect".format(addr))
        else:
            family = socket.AF_INET
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.connect(addr)
        return sock


class SafeStreamSocket:
    def __init__(self, addr: Union[str, typing.Tuple[str, int], socket.socket, Any]):
        """
        Args:
            addr: can be /var/run/usbmuxd or localhost:27015 or (localhost, 27015)
        """
        self._dup_sock = None  # keep original sock when switch_to_ssl
        self._name = None

        try:
            self._sock = create_socket(addr)
        except Exception as e:
            raise SocketError("socket connect error") from e

        self._finalizer = weakref.finalize(self, self._cleanup)

    def _cleanup(self):
        sock = self._dup_sock or self._sock
        try:
            sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        sock.close()

    def close(self):
        logger.debug("Closing socket")
        self._finalizer()

    @property
    def closed(self) -> bool:
        return not self._finalizer.alive

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, new_name: str):
        self._name = new_name

    def get_socket(self) -> socket.socket:
        return self._sock

    def recv(self, buffer_size: int = 4096) -> bytes:
        """recv data from socket
        Args:
            buffer_size: buffer size

        Raises:
            SocketError
        """
        try:
            return self._sock.recv(buffer_size)
        except socket.timeout as e:
            raise SocketError("socket timeout") from e
        except Exception as e:
            raise SocketError("socket error") from e

    def recvall(self, size: int) -> bytearray:
        buf = bytearray()
        while len(buf) < size:
            chunk = self.recv(size - len(buf))
            if not chunk:
                raise SocketError("recvall: socket connection broken")
            buf.extend(chunk)
        return buf

    def sendall(self, data: Union[bytes, bytearray]):
        try:
            return self._sock.sendall(data)
        except Exception as e:
            raise SocketError("sendall error") from e

    def __enter__(self):
        return self

    def __exit__(self, *args):
        logger.debug("Closing socket __exit__")
        self.close()


class PlistSocket(SafeStreamSocket):
    def __init__(self, addr: str, tag: int = 0):
        super().__init__(addr)
        if isinstance(addr, PlistSocket):
            self._tag = addr._tag
            self._first = addr._first
        else:
            self._tag = tag
            self._first = True
        self.prepare()

    def prepare(self):
        pass

    def send_packet(self, payload: dict, message_type: int = 8):
        """
        Args:
            payload: required

            # The following args only used in the first request
            message_type: 8 (Plist)
        """

        body_data = plistlib.dumps(payload)
        if self._first:  # first package
            length = 16 + len(body_data)
            header = struct.pack(
                "IIII", length, 1, message_type,
                self._tag)  # version: 1, request: 8(?), tag: 1(?)
        else:
            header = struct.pack(">I", len(body_data))
        self.sendall(header + body_data)

    def recv_packet(self, header_size=None) -> dict:
        if self._first or header_size == 16:  # first receive
            header = self.recvall(16)
            (length, version, resp, tag) = struct.unpack("IIII", header)
            length -= 16  # minus header length
            self._first = False
        else:
            header = self.recvall(4)
            (length,) = struct.unpack(">I", header)

        body_data = self.recvall(length)
        payload = plistlib.loads(body_data)
        return payload


class PlistSocketProxy:
    def __init__(self, psock: typing.Union[PlistSocket, "PlistSocketProxy"]):
        self._finalizer = None
        if isinstance(psock, PlistSocketProxy):
            psock._finalizer.detach()
            self.__dict__.update(psock.__dict__)
        else:
            assert isinstance(psock, PlistSocket)
            self._psock = psock

        self._finalizer = weakref.finalize(self, self._psock.close)
        self.prepare()

    @property
    def psock(self) -> PlistSocket:
        return self._psock

    @property
    def name(self) -> str:
        return self.psock.name

    @name.setter
    def name(self, new_name: str):
        self.psock.name = new_name

    def prepare(self):
        pass

    def get_socket(self) -> socket.socket:
        return self.psock.get_socket()

    def send_packet(self, payload: dict, message_type: int = 8):
        return self.psock.send_packet(payload, message_type)

    def recv_packet(self, header_size=None) -> dict:
        return self.psock.recv_packet(header_size)

    def send_recv_packet(self, payload: dict, timeout: float = 10.0) -> dict:
        with set_socket_timeout(self.psock.get_socket(), timeout):
            self.send_packet(payload)
            return self.recv_packet()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def close(self):
        self._finalizer()

    @property
    def closed(self) -> bool:
        return not self._finalizer.alive


def _check(data: dict):
    if 'Number' in data and data['Number'] != 0:
        raise MuxReplyError(data['Number'])


class Usbmux:
    def __init__(self, address: typing.Optional[Union[str, tuple]] = None):
        if address is None:
            if os.name == "posix":  # linux or darwin
                address = "/var/run/usbmuxd"
            elif os.name == "nt":  # windows
                address = ('127.0.0.1', 27015)
            else:
                raise EnvironmentError("Unsupported os.name", os.name)

        self.__address = address
        self.__tag = 0

    @property
    def address(self) -> str:
        if isinstance(self.__address, str):
            return self.__address
        ip, port = self.__address
        return f"{ip}:{port}"

    def _next_tag(self) -> int:
        self.__tag += 1
        return self.__tag

    def create_connection(self) -> PlistSocketProxy:
        psock = PlistSocket(self.__address, self._next_tag())
        return PlistSocketProxy(psock)

    def send_recv(self, payload: dict, timeout: float = None) -> dict:
        s = self.create_connection()
        data = s.send_recv_packet(payload, timeout)
        _check(data)
        return data

    def device_list(self) -> typing.List[Any]:
        """
        Return DeviceInfo and contains bother USB and NETWORK device

        Data processing example:
        {'DeviceList': [{'DeviceID': 37,
                'MessageType': 'Attached',
                'Properties': {'ConnectionSpeed': 480000000,
                            'ConnectionType': 'USB',
                            'DeviceID': 37,
                            'LocationID': 341966848,
                            'ProductID': 4776,
                            'SerialNumber': '539c5fffb18f2be0bf7f771d68f7c327fb68d2d9',
                            'UDID': '539c5fffb18f2be0bf7f771d68f7c327fb68d2d9',
                            'USBSerialNumber': '539c5fffb18f2be0bf7f771d68f7c327fb68d2d9'}}]}
        """
        payload = {
            "MessageType": "ListDevices",  # 必选
            "ClientVersionString": "libusbmuxd 1.1.0",
            "ProgName": PROGRAM_NAME,
            "kLibUSBMuxVersion": 3,
            # "ProcessID": 0, # Xcode send it processID
        }
        data = self.send_recv(payload, timeout=10)
        result = {}
        for item in data['DeviceList']:
            prop = item['Properties']
            prop['ConnectionType'] = prop['ConnectionType'].lower()  # 兼容旧代码
            result[prop.get("UDID")] = prop
        return list(result.values())

    def device_udid_list(self) -> typing.List[str]:
        return [d.udid for d in self.device_list()]

    def read_system_BUID(self) -> str:
        """ BUID is always same """
        data = self.send_recv({
            'ClientVersionString': 'libusbmuxd 1.1.0',
            'MessageType': 'ReadBUID',
            'ProgName': PROGRAM_NAME,
            'kLibUSBMuxVersion': 3
        })
        return data['BUID']

    def watch_device(self) -> typing.Iterator[dict]:
        """
        Return iterator of data as follows
        - {'DeviceID': 59, 'MessageType': 'Detached'}
        - {'DeviceID': 59, 'MessageType': 'Attached', 'Properties': {
            'ConnectionSpeed': 100,
            'ConnectionType': 'USB',
            'DeviceID': 59,
            'LocationID': 341966848, 'ProductID': 4776,
            'SerialNumber': 'xxx.xxx', 'USBSerialNumber': 'xxxx..xxx'}}
        """
        with self.create_connection() as s:
            s.send_packet({
                'ClientVersionString': 'qt4i-usbmuxd',
                'MessageType': 'Listen',
                'ProgName': 'tcprelay'
            })
            data = s.recv_packet()
            _check(data)

            while True:
                data = s.recv_packet(header_size=16)
                yield data

    def connect_device_port(self, devid: int, port: int) -> PlistSocketProxy:
        """
        Create connection to mobile phone
        """
        _port = socket.htons(port)
        # Same as: ((port & 0xff) << 8) | (port >> 8)
        del port

        conn = self.create_connection()
        payload = {
            'DeviceID': devid,  # Required
            'MessageType': 'Connect',  # Required
            'PortNumber': _port,  # Required
            'ProgName': PROGRAM_NAME,
        }

        logger.debug("Send payload: %s", payload)
        data = conn.send_recv_packet(payload)
        _check(data)
        logger.debug("connected to port: %d", _port)
        return conn
