# Monkey patch the stdlib for gevent - this _must_ happen here, as early as
# possible, to avoid problems with the stdlib usage elsewhere in pyinfra. API
# scripts should also patch gevent at the start of their execution.
from gevent import monkey  # noqa

monkey.patch_all()  # noqa
