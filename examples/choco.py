from pyinfra import host
from pyinfra.modules import choco

SHELL = 'ps'

# TODO: Is there a better way to determine if windows?
computer_info = host.fact.windows_computer_info
if computer_info:
    product_name = computer_info['WindowsProductName']
    if product_name:
        if product_name.split()[0] == 'Windows':

            # install Chocolately
            choco.install()

            choco.packages(
                {'Install notepadplusplus'},
                'notepadplusplus',
            )
