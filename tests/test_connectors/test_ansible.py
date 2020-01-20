from os import path
from unittest import TestCase

from pyinfra.api.connectors.ansible import make_names_data
from pyinfra.api.exceptions import InventoryError


class TestAnsibleConnector(TestCase):
    def test_make_names_data_with_limit(self):
        data = make_names_data(inventory_filename=path.join(
            'tests', 'deploy', 'inventories', 'inventory_ansible',
        ))

        assert data == [
            ('webserver-1.net', {}, ['web_and_db_servers', 'webservers']),
            ('webserver-2.net', {}, ['web_and_db_servers', 'webservers']),
            ('webserver-3.net', {}, ['web_and_db_servers', 'webservers']),
            ('dbserver-01.net', {}, ['dbservers', 'web_and_db_servers']),
            ('dbserver-02.net', {}, ['dbservers', 'web_and_db_servers']),
        ]

    def test_make_names_data_no_file(self):
        with self.assertRaises(InventoryError):
            make_names_data(inventory_filename='/not/a/file')
