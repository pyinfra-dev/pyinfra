from pathlib import Path

from pyinfra_testing.operations import make_operation_tests

OPS_BASE_IMPORT_PATH = "pyinfra.operations"
OPS_TESTS_BASE_FOLDER = Path(__file__).parent / "operations"


# Find available operation tests
operations = sorted(
    [filename.name for filename in OPS_TESTS_BASE_FOLDER.iterdir() if filename.is_dir()],
)

# Generate the classes, attaching to locals
for operation_name in operations:
    locals()[operation_name] = make_operation_tests(
        OPS_BASE_IMPORT_PATH, operation_name, OPS_TESTS_BASE_FOLDER / operation_name
    )
