def make_stat_cat_command(*filenames):
    commands = [
        '(! stat {0} 2> /dev/null || cat {0})'.format(filename)
        for filename in filenames
    ]
    return ' && '.join(commands)
