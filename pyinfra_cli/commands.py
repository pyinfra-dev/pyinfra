import json

from .exceptions import CliError
from .util import parse_cli_arg, try_import_module_attribute


def get_func_and_args(commands):
    operation_name = commands[0]

    op = try_import_module_attribute(operation_name, prefix="pyinfra.operations")

    # Parse the arguments
    operation_args = commands[1:]

    if len(operation_args) == 1:
        # Check if we're JSON (in which case we expect a list of two items:
        # a list of args and a dict of kwargs).
        try:
            args, kwargs = json.loads(operation_args[0])
            return op, (args or (), kwargs or {})
        except ValueError:
            pass

    args = [parse_cli_arg(arg) for arg in operation_args if "=" not in arg]

    kwargs = {
        key: parse_cli_arg(value)
        for key, value in [arg.split("=", 1) for arg in operation_args if "=" in arg]
    }

    return op, (args, kwargs)


def get_facts_and_args(commands):
    facts = []

    current_fact = None

    for command in commands:
        if "=" in command:
            if not current_fact:
                raise CliError("Invalid fact commands: `{0}`".format(commands))

            key, value = command.split("=", 1)
            current_fact[2][key] = value
            continue

        if current_fact:
            facts.append(current_fact)
            current_fact = None

        if "." not in command:
            raise CliError(f"Invalid fact: `{command}`, should be in the format `module.cls`")

        fact_cls = try_import_module_attribute(command, prefix="pyinfra.facts")
        current_fact = (fact_cls, (), {})

    if current_fact:
        facts.append(current_fact)

    return facts
