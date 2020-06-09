from pyinfra.operations import files

SUDO = True

# Run: pyinfra @docker/ubuntu files_line_with_quotes.py

line = 'QUOTAUSER=""'
results = files.line(
    {'Example with double quotes (")'},
    '/etc/adduser.conf',
    '^{}$'.format(line),
    replace=line,
)
print(results.changed)
