import contextlib
import socket
import typing
import unicodedata


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


def unicode_len(s: str) -> int:
    """ printable length of string """
    length = 0
    for char in s:
        if unicodedata.east_asian_width(char) in ('F', 'W'):
            length += 2
        else:
            length += 1
    return length


def ljust(s, length: int):
    s = str(s)
    return s + ' ' * (length - unicode_len(s))


def print_dict_as_table(dict_values: list[dict], headers: list[str], sep: str = "\t"):
    """
    Output as format
    ----------------------------------------
    Identifier                DeviceName ProductType ProductVersion ConnectionType
    00000000-1234567890123456 MIMM       iPhone13,3  17.2           USB
    """
    header_with_lengths = []
    for header in headers:
        if dict_values:
            max_len = max([unicode_len(str(item.get(header, ""))) for item in dict_values])
        else:
            max_len = 0
        header_with_lengths.append((header, max(max_len, unicode_len(header))))
    rows = []
    # print header
    for header, _len in header_with_lengths:
        rows.append(ljust(header, _len))
    print(sep.join(rows).rstrip())
    # print rows
    for item in dict_values:
        rows = []
        for header, _len in header_with_lengths:
            rows.append(ljust(item.get(header, ""), _len))
        print(sep.join(rows).rstrip())
