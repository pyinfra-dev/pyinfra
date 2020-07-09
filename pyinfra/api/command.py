from six.moves import shlex_quote

from .operation_kwargs import get_executor_kwarg_keys


class MaskString(str):
    pass


class QuoteString(object):
    def __init__(self, obj):
        self.object = obj


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


class StringCommand(PyinfraCommand):
    def __init__(self, *bits, **kwargs):
        super(StringCommand, self).__init__(**kwargs)
        self.bits = bits

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

            if quote:
                bit = shlex_quote(bit)

            all_bits.append(bit)

        return all_bits

    def get_raw_value(self):
        return ' '.join(self._get_all_bits(lambda bit: bit.get_raw_value()))

    def get_masked_value(self):
        return ' '.join([
            '***' if isinstance(bit, MaskString) else bit
            for bit in self._get_all_bits(lambda bit: bit.get_masked_value())
        ])


class FileUploadCommand(PyinfraCommand):
    def __init__(self, src, dest, **kwargs):
        super(FileUploadCommand, self).__init__(**kwargs)
        self.src = src
        self.dest = dest

    def __repr__(self):
        return 'FileUploadCommand({0}, {1})'.format(self.src, self.dest)


class FileDownloadCommand(PyinfraCommand):
    def __init__(self, src, dest, **kwargs):
        super(FileDownloadCommand, self).__init__(**kwargs)
        self.src = src
        self.dest = dest

    def __repr__(self):
        return 'FileDownloadCommand({0}, {1})'.format(self.src, self.dest)


class FunctionCommand(PyinfraCommand):
    def __init__(self, function, args, func_kwargs, **kwargs):
        super(FunctionCommand, self).__init__(**kwargs)
        self.function = function
        self.args = args
        self.kwargs = func_kwargs

    def __repr__(self):
        return 'FunctionCommand({0})'.format(self.function.__name__)
