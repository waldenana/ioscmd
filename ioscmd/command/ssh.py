from ioscmd.command.cli import cli, ssh_client
from ioscmd.ssh_client import SSH


@cli.command()
@ssh_client
def ssh(client: SSH):
    client()
