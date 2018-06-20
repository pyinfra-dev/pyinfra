import os

from redbaron import ElifNode, ElseNode, RedBaron

from pyinfra import logger


def _replace_ifs(red):
    if_groups = red.find_all('IfelseblockNode', recursive=False)

    # For each if/elif/else group
    for if_group in if_groups:
        if_tests = []

        # Each individual if/elif/else block
        for block in if_group.value:
            if_type = 'if'

            # If we're ending a series of if/elif statements with else, we want
            # to not all the positive tests.
            if isinstance(block, ElseNode):
                if_type = 'else'
                test_code = 'not (({0}))'.format(
                    ') and ('.join(if_tests),
                )
            else:
                test_code = test_code_original = block.test.dumps()

                # If we're an elif node we want to test for the elif *and* not
                # any previous if tests.
                if isinstance(block, ElifNode):
                    if_type = 'elif'
                    test_code = '({0}) and not (({1}))'.format(
                        test_code,
                        ') and ('.join(if_tests),
                    )

                # Now we append the original test
                if_tests.append(test_code_original)

            # Set the value (pass) to the parsed nested block value
            new_value = block.value
            new_value = _replace_ifs(new_value)

            with_node = RedBaron(
                'with state.when({0}): pass'.format(test_code),
            )[0]
            with_node.value = new_value

            # Finally, replace the if/elif/else block with our state.when(...)
            block_test = ''
            if if_type != 'else':
                block_test = ' {0}'.format(block.test)

            logger.debug('Replacing "{0}{1}" -> "with {2}"'.format(
                if_type, block_test, with_node.contexts[0],
            ))
            block.replace(with_node)

    return red


def compile_deploy_code(code):
    if os.environ.get('PYINFRA_COMPILE') == 'off':
        return code

    red = RedBaron(code)
    _replace_ifs(red)

    return red.dumps()


def compile_deploy_file(filename):
    with open(filename, 'r') as f:
        code = f.read()

    return compile_deploy_code(code)
