from pyinfra.facts.util.units import parse_human_readable_size


def test_parse_human_readable_size():
    example_strings = [
        "1024b",
        "10.43 KB",
        "11 GB",
        "343.1 MB",
        "10.43KB",
        "11GB",
        "343.1MB",
        "10.43 kb",
        "11 gb",
        "343.1 mb",
        "10.43kb",
        "11gb",
        "343.1mb",
        "1024Kib",
        "10.43 KiB",
        "11 GiB",
        "343.1 MiB",
        "10.43KiB",
        "11GiB",
        "343.1MiB",
        "10.43 kib",
        "11 gib",
    ]
    for example_string in example_strings:
        print(example_string, parse_human_readable_size(example_string))
