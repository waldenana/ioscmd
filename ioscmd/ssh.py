import os
import re
import select
import subprocess
import sys
import termios
import time
import tty

import paramiko
from paramiko.config import SSH_PORT

from .exceptions import AuthenticationException
from .relay import Usbmux


def resize_pty(channel):
    # resize to match terminal size
    tty_height, tty_width = subprocess.check_output(['stty', 'size']).split()
    try:
        channel.resize_pty(width=int(tty_width), height=int(tty_height))
    except paramiko.ssh_exception.SSHException:
        pass


class SSH(paramiko.SSHClient):

    def __init__(self):
        paramiko.SSHClient.__init__(self)
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._info = None
        self._relay = None

    def __del__(self):
        self.close()

    def close(self):
        print("closed ssh connection")
        super().close()

    def connect(
            self,
            hostname,
            port=SSH_PORT,
            username=None,
            password=None, *args
    ):
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        socket = None
        if not hostname or not re.match(ip_pattern, hostname):
            socket = self._create_proxy(hostname, port)
        try:
            super().connect(hostname=hostname, port=port, username=username, password=password, sock=socket, *args)
        except paramiko.ssh_exception.AuthenticationException:
            raise AuthenticationException('SSH connection failed')

    def _create_proxy(self, host, port):
        _usbmux = Usbmux()
        devices = _usbmux.device_list()
        if host is None:
            if len(devices) >= 2:
                raise AuthenticationException("More than 2 usb devices detected")
            self._info = devices[0]
        elif len(devices) == 0:
            raise AuthenticationException("No local device detected")
        else:
            for d in devices:
                if d["UDID"] == host:
                    self._info = d
        if self._info is None:
            raise AuthenticationException('Device not found')
        time.sleep(2)
        conn = _usbmux.connect_device_port(self._info['DeviceID'], int(port))
        self._socket = conn
        return conn.get_socket()

    def __call__(self, *args, **kwargs):
        oldtty_attrs = termios.tcgetattr(sys.stdin)
        client = self.invoke_shell()
        try:
            stdin_fileno = sys.stdin.fileno()
            # 将现在的操作终端属性设置为服务器上的原生终端属性,可以支持tab了
            tty.setraw(stdin_fileno)
            tty.setcbreak(stdin_fileno)
            client.settimeout(0)
            while True:
                resize_pty(client)
                read, wr, err = select.select([client, sys.stdin, ], [], [])
                # 如果是用户输入命令了,sys.stdin发生变化
                if sys.stdin in read:
                    # 获取输入的内容，输入一个字符发送1个字符
                    char = os.read(stdin_fileno, 1)
                    # 将命令发送给服务器
                    client.send(char)

                # 服务器返回了结果,channel通道接受到结果,发生变化 select感知到
                if client in read:
                    # 获取结果
                    result = client.recv(1024)
                    # 断开连接后退出
                    if len(result) == 0:
                        break
                    # 输出到屏幕
                    sys.stdout.write(result.decode())
                    sys.stdout.flush()
        finally:
            # 执行完后将现在的终端属性恢复为原操作终端属性
            termios.tcsetattr(sys.stdin, termios.TCSAFLUSH, oldtty_attrs)
