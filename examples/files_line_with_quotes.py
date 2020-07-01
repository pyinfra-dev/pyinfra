from pyinfra.operations import files

SUDO = True

# Run: pyinfra @docker/ubuntu files_line_with_quotes.py

line = 'QUOTAUSER=""'
results = files.line(
    name='Example with double quotes (")',
    path='/etc/adduser.conf',
    line='^{}$'.format(line),
    replace=line,
)
print(results.changed)
