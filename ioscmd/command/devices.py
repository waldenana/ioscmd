from pathlib import Path

import click

from ioscmd.command.cli import cli, ssh_client
from ioscmd.sockets import Usbmux
from ioscmd.ssh_client import SSH
from ioscmd.utils import print_dict_as_table


@cli.command()
def devices():
    _usbmux = Usbmux()
    devices = _usbmux.device_list()
    headers = ["Identifier", "DeviceName", "WiFiAddress", "ProductType", "ProductVersion", "ConnectionType"]
    infos = []
    for device in devices:
        info = _usbmux.get_deviceInfo(device['DeviceID'])
        info['Identifier'] = device["UDID"]
        info['ConnectionType'] = device["ConnectionType"]
        infos.append(info)
    print_dict_as_table(infos, headers)
