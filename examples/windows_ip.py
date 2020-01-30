from pyinfra import host

print(host.fact.windows_network_configuration['windows_network_configuration']
      ['Index']['1']['IPAddress'])
