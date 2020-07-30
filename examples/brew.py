from pyinfra.operations import brew

# To run: "pyinfra @local brew.py"

brew.packages(
    name='Install latest Vim',
    packages=['vim'],
    update=True,
)

brew.casks(
    name='Upgrade and install the latest package via casks',
    casks=['godot'],
    upgrade=True,
    latest=True,
)

brew.tap(
    name='Add a brew tap',
    src='ktr0731/evans',
)

# multiple taps
taps = ['includeos/includeos', 'ktr0731/evans']
for tap in taps:
    brew.tap(
        name='Add brew tap {}'.format(tap),
        src=tap,
    )
