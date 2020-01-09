from pyinfra import host
from pyinfra.modules import brew

brew.packages(
    {'Install latest Vim'},
    ['vim'],
    update=True,
)

brew.casks(
    {'Upgrade and install the latest package via casks'},
    ['godot'],
    upgrade=True,
    latest=True,
)

brew.tap(
    {'Add a brew tap'},
    'ktr0731/evans',
)
