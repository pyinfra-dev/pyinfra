# pyinfra
# File: docs/build.py
# Desc: boostraps pydocs to auto-generate module documentation

# Monkey patch things first
from gevent.monkey import patch_all
patch_all()

# Import host so pyinfra.host exists
from pyinfra.api import host # noqa

# Now we run pydocs
from pydocs import main
main()
