import click

from ioscmd.command.cli import cli, ssh_client
from ioscmd.ssh_client import SSH


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("cmd", nargs=-1, required=True)
@ssh_client
def shell(client: SSH, cmd):
    _, stdout, stderr = client.exec_command(" ".join(cmd))
    while True:
        line = stdout.readline()
        if not line:
            break
        print(line.rstrip())
