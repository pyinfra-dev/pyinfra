from pyinfra.operations import pacman

SUDO = True

pacman.packages(
    {'Install Vim and a plugin'},
    ['vim-fugitive', 'vim'],
    update=True,
)
