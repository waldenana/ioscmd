from functools import update_wrapper

import click
from click import ClickException

from ioscmd.ssh_client import SSH


@click.group()
@click.option('--ip', "-i", default=None, help='ssh host ip')
@click.option('--port', "-p", default="22", help='ssh port')
@click.option('--udid', "-u", default=None, help='specify unique device identifier')
@click.pass_context
def cli(ctx: click.Context, ip, port, udid):
    ctx.ensure_object(dict)
    ctx.obj['udid'] = udid
    ctx.obj['port'] = port
    ctx.obj['ip'] = ip


def ssh_client(func):
    @click.pass_context
    def new_func(ctx, *args, **kwargs):
        ip = ctx.obj['ip']
        udid = ctx.obj['udid']
        local_port = ctx.obj['port']
        with SSH() as _client:
            try:
                _client.connect(hostname=ip if ip else udid, port=local_port, username='root', password='alpine')
            except Exception as e:
                raise ClickException(str(e))
            return ctx.invoke(func, _client, *args, **kwargs)

    return update_wrapper(new_func, func)


CLI_GROUPS = ["ssh", "install", "upload", "devices", "shell", "pull"]
for group in CLI_GROUPS:
    __import__(f"ioscmd.command.{group}")
