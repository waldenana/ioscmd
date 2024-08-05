# 这是一个示例 Python 脚本。
import os
import warnings
from pathlib import Path

import click
from click import ClickException

warnings.filterwarnings(action='ignore', module='.*paramiko.*')
ssh_client = None


@click.group()
@click.option('--ip', "-i", default=None, help='ssh host ip')
@click.option('--port', "-p", default="22", help='ssh port')
@click.option('--udid', "-u", default=None, help='specify unique device identifier')
def main(ip, port, udid):
    local_port = port
    # 连接SSH服务端，以用户名和密码进行认证
    try:
        ssh_client.connect(hostname=ip if ip else udid, port=local_port, username='root', password='alpine')
    except Exception as e:
        raise ClickException(str(e))


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
            print(f"upload file {local_file} to {remote_path}")
            sftp.put(local_file, remote_path)

    _listdir(local, remote)


def _shell(cmd):
    _, stdout, stderr = ssh_client.exec_command(cmd)

    while True:
        line = stdout.readline()
        if not line:
            break
        print(line.rstrip(), end="")


@click.command(context_settings={"ignore_unknown_options": True})
@click.argument("cmd", nargs=-1, required=True)
def shell(cmd):
    _shell(" ".join(cmd))


@click.command()
def ssh():
    ssh_client()


main.add_command(install)
main.add_command(push)
main.add_command(shell)
main.add_command(ssh)


def __main__():
    from .ssh import SSH
    global ssh_client
    ssh_client = SSH()
    main(standalone_mode=False)
    ssh_client.close()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    __main__()
