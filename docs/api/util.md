## pyinfra.api.util


### class: AttrDict

##### method: AttrDict.__init__

```py
AttrDict.__init__(
    self,
    attrs
)
```

##### method: AttrDict.dict

```py
AttrDict.dict(
    self
)
```


### class: FallbackAttrDict

##### method: FallbackAttrDict.__init__

```py
FallbackAttrDict.__init__(
    self,
    *datas
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
