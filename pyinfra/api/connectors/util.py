from socket import timeout as timeout_error
from subprocess import PIPE, Popen

import click
import gevent

from gevent.queue import Queue

from pyinfra import logger
from pyinfra.api.util import read_buffer


def run_local_process(
    command,
    stdin=None,
    timeout=None,
    print_output=False,
    print_prefix=None,
):
    process = Popen(command, shell=True, stdout=PIPE, stderr=PIPE, stdin=PIPE)

    if stdin:
        write_stdin(stdin, process.stdin)

    combined_output = read_buffers_into_queue(
        process.stdout,
        process.stderr,
        timeout=timeout,
        print_output=print_output,
        print_prefix=print_prefix,
    )

    logger.debug('--> Waiting for exit status...')
    process.wait()
    logger.debug('--> Command exit status: {0}'.format(process.returncode))

    # Close any open file descriptors
    process.stdout.close()
    process.stderr.close()

    return process.returncode, combined_output


def read_buffers_into_queue(
    stdout_buffer, stderr_buffer, timeout, print_output, print_prefix,
):
    output_queue = Queue()

    # Iterate through outputs to get an exit status and generate desired list
    # output, done in two greenlets so stdout isn't printed before stderr. Not
    # attached to state.pool to avoid blocking it with 2x n-hosts greenlets.
    stdout_reader = gevent.spawn(
        read_buffer,
        'stdout',
        stdout_buffer,
        output_queue,
        print_output=print_output,
        print_func=lambda line: '{0}{1}'.format(print_prefix, line),
    )
    stderr_reader = gevent.spawn(
        read_buffer,
        'stderr',
        stderr_buffer,
        output_queue,
        print_output=print_output,
        print_func=lambda line: '{0}{1}'.format(
            print_prefix, click.style(line, 'red'),
        ),
    )

    # Wait on output, with our timeout (or None)
    greenlets = gevent.wait((stdout_reader, stderr_reader), timeout=timeout)

    # Timeout doesn't raise an exception, but gevent.wait returns the greenlets
    # which did complete. So if both haven't completed, we kill them and fail
    # with a timeout.
    if len(greenlets) != 2:
        stdout_reader.kill()
        stderr_reader.kill()

        raise timeout_error()

    return list(output_queue.queue)


def split_combined_output(combined_output):
    stdout = []
    stderr = []

    for type_, line in combined_output:
        if type_ == 'stdout':
            stdout.append(line)
        elif type_ == 'stderr':
            stderr.append(line)
        else:  # pragma: no cover
            raise ValueError('Incorrect output line type: {0}'.format(type_))

    return stdout, stderr


def write_stdin(stdin, buffer):
    if not isinstance(stdin, (list, tuple)):
        stdin = [stdin]

    for line in stdin:
        if not line.endswith('\n'):
            line = '{0}\n'.format(line)
        line = line.encode()
        buffer.write(line)
    buffer.close()
