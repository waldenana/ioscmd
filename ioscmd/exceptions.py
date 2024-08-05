__all__ = [
    'BaseError', 'MuxError', 'MuxReplyError',
    'AuthenticationException',
    'SocketError'
]

import enum


class UsbmuxReplyCode(int, enum.Enum):
    """
    Ref: https://github.com/libimobiledevice/usbmuxd/blob/master/src/usbmuxd-proto.h
    """
    OK = 0
    BadCommand = 1
    BadDevice = 2
    ConnectionRefused = 3
    BadVersion = 6


class BaseError(OSError):
    pass


class MuxError(BaseError):
    """ Mutex error """
    pass


class MuxReplyError(MuxError):
    def __init__(self, number: int):
        self.reply_code = UsbmuxReplyCode(number)
        super().__init__(self.reply_code)


class SocketError(MuxError):
    """ Socket timeout error """


class AuthenticationException(BaseError):
    pass
