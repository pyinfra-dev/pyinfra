from unittest import TestCase

from pyinfra.api.connectors.util import split_combined_output


class TestConnectorUtil(TestCase):
    def test_split_combined_output_works(self):
        results = split_combined_output([
            ('stdout', 'stdout1'),
            ('stdout', 'stdout2'),
            ('stderr', 'stderr1'),
            ('stdout', 'stdout3'),
        ])

        assert results == (['stdout1', 'stdout2', 'stdout3'], ['stderr1'])

    def test_split_combined_output_raises(self):
        with self.assertRaises(ValueError):
            split_combined_output(['nope', ''])
