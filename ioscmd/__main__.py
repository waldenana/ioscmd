# 这是一个示例 Python 脚本。
import logging
import os
import sys
import time
from pathlib import Path
import warnings
import click

from ioscmd.relay import RelayService

warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)
ssh_client = None


@click.group()
@click.option('--ip', "-i", default="", help='ssh host ip')
@click.option('--port', "-p", default="22", help='ssh port')
@click.option('--udid', "-u", default="", help='specify unique device identifier')
def main(ip, port, udid):
    local_port = port
    ssh_host = ip
    if not ssh_host:
        relay = RelayService(udid, port)
        local_port = relay.start()
        ssh_host = "127.0.0.1"
        time.sleep(2)

    import paramiko
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    # 连接SSH服务端，以用户名和密码进行认证
    client.connect(hostname=ssh_host, port=local_port, username='root', password='alpine')
    global ssh_client
    ssh_client = client


@click.command()
@click.argument("deb", type=click.Path(exists=True))
def install(deb):
    sftp = ssh_client.open_sftp()
    sftp.put(deb, "/tmp/_ios_install.deb")
    _shell("dpkg -i /tmp/_ios_install.deb")
    _shell("apt-get -f -y install")


@click.command()
@click.argument("local", type=click.Path(exists=True))
@click.argument("remote")
def push(local, remote):
    sftp = ssh_client.open_sftp()

    def _listdir(local_file, remote_path):
        if Path(local_file).is_dir():
            try:
                sftp.mkdir(remote_path)
            except Exception as e:
                pass
            files = os.listdir(local_file)
            for file in files:
                file_path = os.path.join(local_file, file)
                _listdir(file_path, os.path.join(remote_path, file))
        else:
            logger.info(f"upload file {local_file} to {remote_path}")
            sftp.put(local_file, remote_path)

    _listdir(local, remote)
    sftp.close()
    ssh_client.close()


def _shell(cmd):
    _, stdout, stderr = ssh_client.exec_command(cmd)

    while True:
        line = stdout.readline()
        if not line:
            break
        print(line)


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("cmd", nargs=-1, required=True)
def shell(cmd):
    print(cmd)
    _shell(" ".join(cmd))


main.add_command(install)
main.add_command(push)
main.add_command(shell)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
    sys.exit()
