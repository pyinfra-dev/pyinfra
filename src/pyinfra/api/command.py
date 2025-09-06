from __future__ import annotations

import shlex
from inspect import getfullargspec
from string import Formatter
from typing import IO, TYPE_CHECKING, Callable, Union

import gevent
from typing_extensions import Unpack, override

from pyinfra.context import LocalContextObject, ctx_config, ctx_host

from .arguments import ConnectorArguments

if TYPE_CHECKING:
    from pyinfra.api.host import Host
    from pyinfra.api.state import State


def make_formatted_string_command(string: str, *args, **kwargs) -> "StringCommand":
    """
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
    """

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


class QuoteString:
    obj: Union[str, "StringCommand"]

    def __init__(self, obj: Union[str, "StringCommand"]):
        self.obj = obj

    @override
    def __repr__(self) -> str:
        return f"QuoteString({self.obj})"


class PyinfraCommand:
    connector_arguments: ConnectorArguments

    def __init__(self, **arguments: Unpack[ConnectorArguments]):
        self.connector_arguments = arguments

    @override
    def __eq__(self, other) -> bool:
        if isinstance(other, self.__class__) and repr(self) == repr(other):
            return True
        return False

    def execute(self, state: "State", host: "Host", connector_arguments: ConnectorArguments):
        raise NotImplementedError


class StringCommand(PyinfraCommand):
    def __init__(
        self,
        *bits,
        _separator=" ",
        **arguments: Unpack[ConnectorArguments],
    ):
        super().__init__(**arguments)
        self.bits = bits
        self.separator = _separator

    @override
    def __str__(self) -> str:
        return self.get_masked_value()

    @override
    def __repr__(self) -> str:
        return f"StringCommand({self.get_masked_value()})"

    def _get_all_bits(self, bit_accessor):
        all_bits = []

        for bit in self.bits:
            quote = False
            if isinstance(bit, QuoteString):
                quote = True
                bit = bit.obj

            if isinstance(bit, StringCommand):
                bit = bit_accessor(bit)

            if not isinstance(bit, str):
                bit = "{0}".format(bit)

            if quote:
                bit = shlex.quote(bit)

            all_bits.append(bit)

        return all_bits

    def get_raw_value(self) -> str:
        return self.separator.join(
            self._get_all_bits(
                lambda bit: bit.get_raw_value(),
            ),
        )

    def get_masked_value(self) -> str:
        return self.separator.join(
            [
                "***" if isinstance(bit, MaskString) else bit
                for bit in self._get_all_bits(lambda bit: bit.get_masked_value())
            ],
        )

    @override
    def execute(self, state: "State", host: "Host", connector_arguments: ConnectorArguments):
        connector_arguments.update(self.connector_arguments)

        return host.run_shell_command(
            self,
            print_output=state.print_output,
            print_input=state.print_input,
            **connector_arguments,
        )


class FileUploadCommand(PyinfraCommand):
    def __init__(
        self,
        src: str | IO,
        dest: str,
        remote_temp_filename=None,
        **kwargs: Unpack[ConnectorArguments],
    ):
        super().__init__(**kwargs)
        self.src = src
        self.dest = dest
        self.remote_temp_filename = remote_temp_filename

    @override
    def __repr__(self):
        return "FileUploadCommand({0}, {1})".format(self.src, self.dest)

    @override
    def execute(self, state: "State", host: "Host", connector_arguments: ConnectorArguments):
        connector_arguments.update(self.connector_arguments)

        return host.put_file(
            self.src,
            self.dest,
            remote_temp_filename=self.remote_temp_filename,
            print_output=state.print_output,
            print_input=state.print_input,
            **connector_arguments,
        )


class FileDownloadCommand(PyinfraCommand):
    def __init__(
        self,
        src: str,
        dest: str | IO,
        remote_temp_filename=None,
        **kwargs: Unpack[ConnectorArguments],
    ):
        super().__init__(**kwargs)
        self.src = src
        self.dest = dest
        self.remote_temp_filename = remote_temp_filename

    @override
    def __repr__(self):
        return "FileDownloadCommand({0}, {1})".format(self.src, self.dest)

    @override
    def execute(self, state: "State", host: "Host", connector_arguments: ConnectorArguments):
        connector_arguments.update(self.connector_arguments)

        return host.get_file(
            self.src,
            self.dest,
            remote_temp_filename=self.remote_temp_filename,
            print_output=state.print_output,
            print_input=state.print_input,
            **connector_arguments,
        )


class FunctionCommand(PyinfraCommand):
    def __init__(
        self,
        function: Callable,
        args,
        func_kwargs,
        **kwargs: Unpack[ConnectorArguments],
    ):
        super().__init__(**kwargs)
        self.function = function
        self.args = args
        self.kwargs = func_kwargs

    @override
    def __repr__(self):
        return "FunctionCommand({0}, {1}, {2})".format(
            self.function.__name__,
            self.args,
            self.kwargs,
        )

    @override
    def execute(self, state: "State", host: "Host", connector_arguments: ConnectorArguments):
        argspec = getfullargspec(self.function)
        if "state" in argspec.args and "host" in argspec.args:
            return self.function(state, host, *self.args, **self.kwargs)

        # If we're already running inside a greenlet (ie a nested callback) just execute the func
        # without any gevent.spawn which will break the local host object.
        if isinstance(host, LocalContextObject):
            self.function(*self.args, **self.kwargs)
            return

        def execute_function() -> None:
            with ctx_config.use(state.config.copy()):
                with ctx_host.use(host):
                    self.function(*self.args, **self.kwargs)

        greenlet = gevent.spawn(execute_function)
        return greenlet.get()


class RsyncCommand(PyinfraCommand):
    def __init__(self, src: str, dest: str, flags, **kwargs: Unpack[ConnectorArguments]):
        super().__init__(**kwargs)
        self.src = src
        self.dest = dest
        self.flags = flags

    @override
    def __repr__(self):
        return "RsyncCommand({0}, {1}, {2})".format(self.src, self.dest, self.flags)

    @override
    def execute(self, state: "State", host: "Host", connector_arguments: ConnectorArguments):
        return host.rsync(
            self.src,
            self.dest,
            self.flags,
            print_output=state.print_output,
            print_input=state.print_input,
            **connector_arguments,
        )
