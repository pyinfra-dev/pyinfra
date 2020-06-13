from os import path
from unittest import TestCase

from pyinfra.api.connectors.ansible import make_names_data
from pyinfra.api.exceptions import InventoryError

TEST_DATA = [
    ('mail.example.com', {}, ['all']),
    ('foo.example.com', {}, ['all', 'webservers']),
    ('bar.example.com', {}, ['all', 'webservers']),
    ('one.example.com', {}, ['all', 'dbservers']),
    ('two.example.com', {}, ['all', 'dbservers']),
    ('three.example.com', {}, ['all', 'dbservers']),
]


class TestAnsibleConnector(TestCase):
    def test_make_names_data_no_file(self):
        with self.assertRaises(InventoryError):
            make_names_data(inventory_filename='/not/a/file')

    def test_make_names_data_ini(self):
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

    def test_make_names_data_json(self):
        data = make_names_data(inventory_filename=path.join(
            'tests', 'deploy', 'inventories', 'inventory_ansible.json',
        ))

        assert data == TEST_DATA

    def test_make_names_data_yaml(self):
        data = make_names_data(inventory_filename=path.join(
            'tests', 'deploy', 'inventories', 'inventory_ansible.yml',
        ))

        assert data == TEST_DATA
