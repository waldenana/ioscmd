import os
from pathlib import Path

import click

from ioscmd.command.cli import cli, ssh_client
from ioscmd.ssh_client import SSH


@cli.command()
@ssh_client
@click.argument("remote")
@click.argument("local", type=click.Path())
def pull(client: SSH, remote, local):
    sftp = client.open_sftp()
    local_path = Path(local)
    if local_path.is_dir():
        remote_path = Path(remote)
        local_path = local_path.joinpath(remote_path.name)
    sftp.get(remote, local_path.as_posix())
    print(f"{remote} has been downloaded to {local}")
