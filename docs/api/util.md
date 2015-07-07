## pyinfra.api.util


##### function: get_file_sha1

Calculates the SHA1 of a file object using a buffer to handle larger files.

```py
get_file_sha1(
    io
)
```


##### function: make_hash

Make a hash from an arbitrary nested dictionary, list, tuple or set, used to generate ID's
for operations based on their name & arguments.

```py
make_hash(
    obj
)
```


##### function: underscore

Transform CamelCase -> snake_case.

```py
underscore(
    name
)
```
