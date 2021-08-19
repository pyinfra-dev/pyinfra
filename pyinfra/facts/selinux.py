from pyinfra.api import FactBase


class FileContext(FactBase):
    '''
    Returns structured SELinux file context data for a specified file.

    .. code:: python
        {
            'user': 'system_u',
            'role': 'object_r',
            'type': 'deafult_t',
            'level': 's0',
        }
    '''

    def command(self, path):
        return 'stat -c %C {0} || exit 0'.format(path)

    def process(self, output):
        context = {}
        components = output[0].split(':')
        context['user'] = components[0]
        context['role'] = components[1]
        context['type'] = components[2]
        context['level'] = components[3]
        return context


class SEBoolean(FactBase):
    '''
    Returns the on/off status of a SELinux Boolean.

    .. code:: python
        host.get_fact(SEBoolean, "httpd_can_network_connect") -> "off"
    '''
    requires_command = 'getsebool'

    def command(self, boolean):
        return 'getsebool {0}'.format(boolean)

    def process(self, output):
        components = output[0].split(' --> ')
        return components[1]
