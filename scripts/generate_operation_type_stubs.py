import os
from pyinfra.api.arguments import OPERATION_KWARGS
from redbaron import RedBaron
from logging import getLogger

logger = getLogger()


def get_global_arg_names():
    arg_names = []
    for arg_group in OPERATION_KWARGS.values():
        for arg in arg_group.keys():
            arg_names.append(f"{arg} = None")
    return arg_names

def create_operation_stub(file_path: str):
    with open(file_path) as f:
        content = f.read()
    red = RedBaron(content)
    operations = red("funcdef", # all function definitions
            lambda node: any([dec("name", "operation") for dec in node.decorators]) # with decorator named "operation"
            )
    if operations:
        global_args = get_global_arg_names()
        ellipses = RedBaron("...")
        stubs = []
        for operation in operations:
            stub = operation.copy()
            stub.value = ellipses
            stub.decorators = []
            stub.arguments.extend(global_args)
            # *args and **kwargs must be moved the end of the argument list
            list_argument_index = None
            for i, argument in enumerate(stub.arguments):
                if argument.type == "list_argument":
                    list_argument_index = i
            if list_argument_index is not None:
                list_arg = stub.arguments[list_argument_index]
                stub.arguments.pop(list_argument_index) # pop does not return the element for some reason
                stub.arguments.append(list_arg)
            dict_argument_index = None
            for i, argument in enumerate(stub.arguments):
                if argument.type == "dict_argument":
                    dict_argument_index = i
            if dict_argument_index is not None:
                dict_arg = stub.arguments[dict_argument_index]
                stub.arguments.pop(dict_argument_index)
                stub.arguments.append(dict_arg)
            stubs.append(stub)
        stub_file_content = "\n\n".join([str(stub) for stub in stubs])
        output_file_path = file_path + "i"
        with open(output_file_path, "w") as f:
            f.write(stub_file_content)
    else:
        logger.info(f"No operations found in file {file_path}")

def create_all_operation_stubs():
    """Assume run from project root"""
    operation_dir = os.path.join("pyinfra", "operations")
    for operation_file in os.listdir(operation_dir):
        full_path = os.path.join(operation_dir, operation_file)
        if os.path.isfile(full_path) and os.path.splitext(full_path)[1] == ".py":
            logger.info(f"generate for file {full_path}")
            create_operation_stub(full_path)


if __name__ == "__main__":
    create_all_operation_stubs()
