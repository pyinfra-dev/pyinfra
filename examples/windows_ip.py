from pyinfra import host
from pyinfra.facts.windows import NetworkConfiguration

# print ip address for all network entries
windows_network_config = host.get_fact(NetworkConfiguration)

for index, data in windows_network_config["Index"]:
    print(data["IPAddress"])
