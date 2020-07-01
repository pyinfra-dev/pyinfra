from pyinfra.operations import pacman

SUDO = True

pacman.packages(
    name='Install Vim and a plugin',
    packages=['vim-fugitive', 'vim'],
    update=True,
)
