from pyinfra import host

# print ip address for all network entries
for index in host.fact.windows_network_configuration['Index']:
    print(host.fact.windows_network_configuration['Index'][index]['IPAddress'])
