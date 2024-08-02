# ioscmd
[![PyPI version](https://badge.fury.io/py/ioscmd.svg)](https://badge.fury.io/py/ioscmd)

# Install
```bash
pip install ioscmd

# or install as Isolated environment
brew install pipx
pipx install ioscmd
```

# Basic usage
```shell
ioscmd install ./some.deb
ioscmd push ./some.deb /tmp/some.deb
ioscmd shell dpkg -l
ioscmd ssh


```