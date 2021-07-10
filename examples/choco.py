from pyinfra import host
from pyinfra.facts.windows import WindowsComputerInfo
from pyinfra.operations import choco


computer_info = host.get_fact(WindowsComputerInfo)
if computer_info:
    product_name = computer_info['WindowsProductName']
    if product_name:
        if product_name.split()[0] == 'Windows':

            # install Chocolately
            choco.install()

            choco.packages(
                name='Install notepadplusplus',
                packages='notepadplusplus',
            )
