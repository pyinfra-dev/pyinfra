def cleanup_words():
    with open('words.txt', 'r') as f:
        data = f.read()

    lines = data.splitlines()
    comment_line = lines[0]
    lines = lines[1:]

    lines = sorted(set(lines))

    lines.insert(0, comment_line)

    with open('words.txt', 'w') as f:
        f.write('\n'.join(lines))
        f.write('\n')


if __name__ == '__main__':
    cleanup_words()
