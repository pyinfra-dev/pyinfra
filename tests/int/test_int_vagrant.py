import pytest


@pytest.mark.int
@pytest.mark.vagrant
def test_int_vagrant(helpers):
    vagrant_dir = 'examples/vagrant'

    helpers.run(
        'vagrant up',
        cwd=vagrant_dir,
        expected_lines=['Machine booted and ready!'],
    )

    helpers.run(
        'pyinfra @vagrant vagrant.py',
        cwd=vagrant_dir,
    )

    helpers.run(
        'vagrant destroy -f',
        cwd=vagrant_dir,
        expected_lines=['Stopping', 'Deleting'],
    )
