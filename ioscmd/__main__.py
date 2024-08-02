# 这是一个示例 Python 脚本。
import os
import warnings
from pathlib import Path

import click

warnings.filterwarnings(action='ignore', module='.*paramiko.*')

ssh_client = None


@click.group()
@click.option('--ip', "-i", default="", help='ssh host ip')
@click.option('--port', "-p", default="22", help='ssh port')
@click.option('--udid', "-u", default="", help='specify unique device identifier')
def main(ip, port, udid):
    local_port = port
    ssh_host = ip
    if ssh_host is None:
        ssh_host = udid
    if ssh_host is None:
        raise ValueError('ssh host or udid must be specified')
    from ssh import SSH, AuthenticationException
    client = SSH()
    # 连接SSH服务端，以用户名和密码进行认证
    try:
        client.connect(hostname=ssh_host, port=local_port, username='root', password='alpine')
    except AuthenticationException:
        raise click.ClickException('SSH connection failed')
    global ssh_client
    ssh_client = client


@click.command()
@click.argument("deb", type=click.Path(exists=True))
def install(deb):
    sftp = ssh_client.open_sftp()
    sftp.put(deb, "/tmp/_ios_install.deb")
    _shell("dpkg -i /tmp/_ios_install.deb")
    _shell("apt-get -f -y install")
    sftp.close()
    ssh_client.close()


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
    sftp.close()
    ssh_client.close()


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
    ssh_client.close()


@click.command()
def ssh():
    ssh_client()
    ssh_client.close()


main.add_command(install)
main.add_command(push)
main.add_command(shell)
main.add_command(ssh)

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()
