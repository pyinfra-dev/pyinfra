import shlex

from string import Formatter

import six

from six.moves import shlex_quote

from .operation_kwargs import get_executor_kwarg_keys


def make_formatted_string_command(string, *args, **kwargs):
    '''
    Helper function that takes a shell command or script as a string, splits it
    using ``shlex.split`` and then formats each bit, returning a ``StringCommand``
    instance with each bit.

    Useful to enable string formatted commands/scripts, for example:

    .. code:: python

        curl_command = make_formatted_string_command(
            'curl -sSLf {0} -o {1}',
            QuoteString(src),
            QuoteString(dest),
        )
    '''

    formatter = Formatter()
    string_bits = []

    for bit in shlex.split(string):
        for item in formatter.parse(bit):
            if item[0]:
                string_bits.append(item[0])
            if item[1]:
                value, _ = formatter.get_field(item[1], args, kwargs)
                string_bits.append(value)

    return StringCommand(*string_bits)


class MaskString(str):
    pass


class QuoteString(object):
    def __init__(self, obj):
        self.object = obj

    def __repr__(self):
        return 'QuoteString({0})'.format(self.object)


class PyinfraCommand(object):
    def __init__(self, *args, **kwargs):
        self.executor_kwargs = {
            key: kwargs[key]
            for key in get_executor_kwarg_keys()
            if key in kwargs
        }

    def __eq__(self, other):
        if isinstance(other, self.__class__) and repr(self) == repr(other):
            return True
        return False

    def execute(self, state, host, executor_kwargs):
        raise NotImplementedError


class StringCommand(PyinfraCommand):
    def __init__(self, *bits, **kwargs):
        super(StringCommand, self).__init__(**kwargs)
        self.bits = bits
        self.separator = kwargs.pop('_separator', ' ')

    def __str__(self):
        return self.get_masked_value()

    def __repr__(self):
        return 'StringCommand({0})'.format(self.get_masked_value())

    def _get_all_bits(self, bit_accessor):
        all_bits = []

        for bit in self.bits:
            quote = False
            if isinstance(bit, QuoteString):
                quote = True
                bit = bit.object

            if isinstance(bit, StringCommand):
                bit = bit_accessor(bit)

            if not isinstance(bit, six.string_types):
                bit = '{0}'.format(bit)

            if quote:
                bit = shlex_quote(bit)

            all_bits.append(bit)

        return all_bits

    def get_raw_value(self):
        return self.separator.join(self._get_all_bits(
            lambda bit: bit.get_raw_value(),
        ))

    def get_masked_value(self):
        return self.separator.join([
            '***' if isinstance(bit, MaskString) else bit
            for bit in self._get_all_bits(lambda bit: bit.get_masked_value())
        ])

    def execute(self, state, host, executor_kwargs):
        executor_kwargs.update(self.executor_kwargs)

        return host.run_shell_command(
            self,
            print_output=state.print_output,
            print_input=state.print_input,
            return_combined_output=True,
            **executor_kwargs
        )


class FileUploadCommand(PyinfraCommand):
    def __init__(self, src, dest, **kwargs):
        super(FileUploadCommand, self).__init__(**kwargs)
        self.src = src
        self.dest = dest

    def __repr__(self):
        return 'FileUploadCommand({0}, {1})'.format(self.src, self.dest)

    def execute(self, state, host, executor_kwargs):
        executor_kwargs.update(self.executor_kwargs)

        return host.put_file(
            self.src, self.dest,
            print_output=state.print_output,
            print_input=state.print_input,
            **executor_kwargs
        )


class FileDownloadCommand(PyinfraCommand):
    def __init__(self, src, dest, **kwargs):
        super(FileDownloadCommand, self).__init__(**kwargs)
        self.src = src
        self.dest = dest

    def __repr__(self):
        return 'FileDownloadCommand({0}, {1})'.format(self.src, self.dest)

    def execute(self, state, host, executor_kwargs):
        executor_kwargs.update(self.executor_kwargs)

        return host.get_file(
            self.src, self.dest,
            print_output=state.print_output,
            print_input=state.print_input,
            **executor_kwargs
        )


class FunctionCommand(PyinfraCommand):
    def __init__(self, function, args, func_kwargs, **kwargs):
        super(FunctionCommand, self).__init__(**kwargs)
        self.function = function
        self.args = args
        self.kwargs = func_kwargs

    def __repr__(self):
        return 'FunctionCommand({0}, {1}, {2})'.format(
            self.function.__name__,
            self.args,
            self.kwargs,
        )

    def execute(self, state, host, executor_kwargs):
        return self.function(state, host, *self.args, **self.kwargs)


class RsyncCommand(PyinfraCommand):
    def __init__(self, src, dest, flags, **kwargs):
        super(RsyncCommand, self).__init__(**kwargs)
        self.src = src
        self.dest = dest
        self.flags = flags

    def __repr__(self):
        return 'RsyncCommand({0}, {1}, {2})'.format(self.src, self.dest, self.flags)

    def execute(self, state, host, executor_kwargs):
        return host.rsync(
            self.src, self.dest, self.flags,
            print_output=state.print_output,
            print_input=state.print_input,
            **executor_kwargs
        )
