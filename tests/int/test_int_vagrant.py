import pytest


@pytest.mark.int
def test_int_vagrant(helpers):
    '''Test vagrant'''
    vagrant_dir = 'examples/vagrant'

    helpers.run('vagrant up', cwd=vagrant_dir,
                expected_stdout_lines=['Machine booted and ready!'],
                expected_stderr_lines=[''])

    helpers.run('pyinfra @vagrant vagrant.py', cwd=vagrant_dir,
                expected_stderr_lines=[''])

    helpers.run('vagrant destroy -f', cwd=vagrant_dir,
                expected_stdout_lines=['Stopping', 'Deleting'],
                expected_stderr_lines=[''])
