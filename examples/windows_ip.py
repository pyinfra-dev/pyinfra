from pyinfra import host
from pyinfra.facts.windows import WindowsNetworkConfiguration


# print ip address for all network entries
windows_network_config = host.get_fact(WindowsNetworkConfiguration)

for index, data in windows_network_config['Index']:
    print(data['IPAddress'])
