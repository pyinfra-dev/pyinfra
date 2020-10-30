def make_cat_files_command(*filenames):
    commands = []

    for filename in filenames:
        if '*' in filename:
            # There's no way to test against a glob expression, so accept anything here
            commands.append('cat {0} || true'.format(filename))
        else:
            commands.append('! test -f {0} || cat {0}'.format(filename))

    if len(commands) > 1:  # if we have multiple, wrap them
        commands = ['({0})'.format(command) for command in commands]

    return ' && '.join(commands)
