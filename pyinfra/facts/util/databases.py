def _remove_prefix(title, remove_prefix):
    if title.startswith(remove_prefix):
        return title[len(remove_prefix) :]

    return title


def parse_columns_and_rows(
    lines,
    delimiter,
    remove_column_prefix=None,
    title_parser=None,
):
    titles = lines[0]
    titles = titles.split(delimiter)

    if title_parser:
        titles = [title_parser(title) for title in titles]

    if remove_column_prefix:
        titles = [_remove_prefix(title, remove_column_prefix) for title in titles]

    rows = []

    for line in lines[1:]:
        bits = line.split(delimiter)
        row = {}

        for i, bit in enumerate(bits):
            row[titles[i]] = bit or None

        rows.append(row)

    return rows
