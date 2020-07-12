from __future__ import absolute_import, unicode_literals

import os

import distro


def get_distro_info(root_dir):
    # We point _UNIXCONFDIR to root_dir
    old_value = distro._UNIXCONFDIR
    distro._UNIXCONFDIR = os.path.join(root_dir, 'etc')

    obj = distro.LinuxDistribution(include_lsb=False, include_uname=False)

    # NOTE: The parsing of LinuxDistribution distro information is done in a lazy way.
    # This will force the parsing to happen before we restore the old value of _UNIXCONFDIR.
    _ = obj.info()

    distro._UNIXCONFDIR = old_value
    return obj
