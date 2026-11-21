from pyinfra import config, host
from pyinfra.operations import files

files.template(
    src="jinja.j2",
    dest="/jinja-configured",
)

config.JINJA_GLOBALS = {**config.JINJA_GLOBALS, "application": host.name}
files.template(
    src="jinja.j2",
    dest="/jinja-local",
)

files.template(
    src="jinja.j2",
    dest="/jinja-overridden",
    jinja_env_kwargs={"keep_trailing_newline": True},
    jinja_filters={"shout": str.lower},
    jinja_globals={"application": "OVERRIDE", "count": 0},
    jinja_tests={"positive": lambda value: value >= 0},
)

files.template(
    src="jinja.j2",
    dest="/jinja-render-data",
    application="render",
    count=0,
)
