import os

try:
    from distro import distro
except ImportError:
    import distro  # type: ignore


def get_distro_info(root_dir):
    # We point _UNIXCONFDIR to root_dir
    old_value = distro._UNIXCONFDIR
    distro._UNIXCONFDIR = os.path.join(root_dir, "etc")

    obj = distro.LinuxDistribution(include_lsb=False, include_uname=False)

    # Fixes a bug in distro: https://github.com/python-distro/distro/issues/309
    obj._uname_info = {}

    # NOTE: The parsing of LinuxDistribution distro information is done in a lazy way.
    # This will force the parsing to happen before we restore the old value of _UNIXCONFDIR.
    _ = obj.info()

    distro._UNIXCONFDIR = old_value
    return obj
