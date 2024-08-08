import click

from ioscmd.command.cli import cli, ssh_client
from ioscmd.ssh_client import SSH


@cli.command()
@click.argument("deb", type=click.Path(exists=True))
@ssh_client
def install(client, deb):
    sftp = client.open_sftp()
    sftp.put(deb, "/tmp/_ios_install.deb")
    _shell(client, "dpkg -i /tmp/_ios_install.deb")
    _shell(client, "apt-get -f -y install")
    sftp.close()


def _shell(client, cmd):
    _, stdout, stderr = client.exec_command(cmd)
    while True:
        line = stdout.readline()
        if not line:
            break
        print(line.rstrip())
