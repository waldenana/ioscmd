import contextlib
import socket
import typing


@contextlib.contextmanager
def set_socket_timeout(conn: typing.Union[typing.Callable[..., socket.socket], socket.socket], value: float):
    """Set conn.timeout to value
    Save previous value, yield, and then restore the previous value
    If 'value' is None, do nothing
    """

    def get_conn() -> socket.socket:
        return conn() if callable(conn) else conn

    old_value = get_conn().timeout
    get_conn().settimeout(value)
    try:
        yield
    finally:
        try:
            get_conn().settimeout(old_value)
        except:
            pass
