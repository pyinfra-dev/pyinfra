# pyinfra
# File: pyinfra/cli/fake.py
# Desc: fake objects for the CLI


class FakeData(object):
    # Conversion to other types
    def __str__(self):
        return 'FakeData'

    def __bool__(self):
        return True

    def __int__(self):
        return 1

    def __float__(self):
        return 1.0

    def __long__(self):
        return long(1)

    def __call__(self, *args, **kwargs):
        return FakeData()

    # Interaction with other types
    def __add__(self, other):
        return FakeData()

    def __radd__(self, other):
        return FakeData()

    def __lt__(self, other):
        return True

    def __gt__(self, other):
        return True

    def __le__(self, other):
        return True

    def __ge__(self, other):
        return True

    # Object use
    def __contains__(self, key):
        return True

    def __getattr__(self, key):
        return FakeData()

    def __getitem__(self, key):
        return FakeData()

    def __len__(self):
        return 0

    def __iter__(self):
        yield FakeData()

    def iteritems(self):
        return iter([(FakeData(), FakeData())])


class FakeState(FakeData):
    active = False
    deploy_dir = ''


class FakeHost(FakeData):
    pass


class FakeInventory(FakeData):
    pass
