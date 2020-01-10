from pyinfra.modules import brew

# To run: "pyinfra @local brew.py"

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

# multiple taps
taps = ['includeos/includeos', 'ktr0731/evans']
for tap in taps:
    brew.tap(
        {f'Add brew tap {tap}'},
        tap,
    )
