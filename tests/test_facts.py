from pathlib import Path

from pyinfra_testing.facts import make_fact_tests

FACTS_BASE_IMPORT_PATH = "pyinfra.facts"
FACTS_TESTS_BASE_FOLDER = Path(__file__).parent / "facts"

# Find available fact tests
fact_tests = sorted(
    [filename.name for filename in FACTS_TESTS_BASE_FOLDER.iterdir() if filename.is_dir()],
)

# Generate the classes, attaching to locals
for fact_name in fact_tests:
    locals()[fact_name] = make_fact_tests(
        FACTS_BASE_IMPORT_PATH, fact_name, FACTS_TESTS_BASE_FOLDER / fact_name
    )
