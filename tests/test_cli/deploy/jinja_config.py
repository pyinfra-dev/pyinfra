from jinja2 import FileSystemLoader

from pyinfra import config

config.JINJA_ENV_KWARGS = {"keep_trailing_newline": False, "loader": FileSystemLoader("templates")}
config.JINJA_FILTERS = {"shout": str.upper, "label": str.capitalize}
config.JINJA_GLOBALS = {"application": "configured", "count": 1}
config.JINJA_TESTS = {"positive": lambda value: value > 0}
