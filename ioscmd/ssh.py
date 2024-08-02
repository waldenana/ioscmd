import re
import select
import sys
import termios
import time
import tty

import paramiko
from relay import RelayService
from paramiko.config import SSH_PORT


class AuthenticationException(Exception):
    pass


class SSH(paramiko.SSHClient):

    def __init__(self):
        paramiko.SSHClient.__init__(self)
        self.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    def connect(
            self,
            hostname,
            port=SSH_PORT,
            username=None,
            password=None, *args
    ):
        ip_pattern = r'\b(?:\d{1,3}\.){3}\d{1,3}\b'
        if not re.match(ip_pattern, hostname):
            relay = RelayService(hostname, port)
            port = relay.start()
            hostname = "127.0.0.1"
            time.sleep(2)
            self._relay = relay
            try:
                super().connect(hostname=hostname, port=port, username=username, password=password, *args)
            except paramiko.ssh_exception.AuthenticationException:
                raise AuthenticationException('SSH connection failed')

    def close(self):
        super().close()
        if self._relay is not None:
            self._relay.stop()

    def __call__(self, *args, **kwargs):
        client = self.invoke_shell()
        oldtty = termios.tcgetattr(sys.stdin)
        try:
            # 将现在的操作终端属性设置为服务器上的原生终端属性,可以支持tab了
            tty.setraw(sys.stdin)
            client.settimeout(0)
            while True:
                read, wr, err = select.select([client, sys.stdin, ], [], [])
                # 如果是用户输入命令了,sys.stdin发生变化
                if sys.stdin in read:
                    # 获取输入的内容，输入一个字符发送1个字符
                    input_cmd = sys.stdin.read(1).encode()
                    # 将命令发送给服务器
                    client.sendall(input_cmd)

                # 服务器返回了结果,channel通道接受到结果,发生变化 select感知到
                if client in read:
                    # 获取结果
                    result = client.recv(1024)
                    # 断开连接后退出
                    if len(result) == 0:
                        print("\r\n**** EOF **** \r\n")
                        break
                    # 输出到屏幕
                    sys.stdout.write(result.decode())
                    sys.stdout.flush()
        finally:
            # 执行完后将现在的终端属性恢复为原操作终端属性
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)
