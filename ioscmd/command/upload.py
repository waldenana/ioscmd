import os
from pathlib import Path

import click

from ioscmd.command.cli import cli, ssh_client
from ioscmd.ssh_client import SSH


@cli.command()
@ssh_client
@click.argument("local", type=click.Path(exists=True))
@click.argument("remote")
def push(client: SSH, local, remote):
    sftp = client.open_sftp()

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
