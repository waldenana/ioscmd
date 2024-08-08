# 这是一个示例 Python 脚本。
import warnings

warnings.filterwarnings(action='ignore', module='.*paramiko.*')


def main():
    from ioscmd.command.cli import cli
    cli()


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    main()