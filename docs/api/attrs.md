## pyinfra.api.attrs

This file contains helpers/classes which allow us to have base type (str, int, etc) like operation
arguments while also being able to keep track of the original reference (ie the 'x' in host.data.x).
This means we can generate one operation hash based on an argument host.data.x where host.data.x
changes between hosts. The same logic is applied to facts.

### class: AttrBase


### class: AttrData

##### method: AttrData.__init__

```py
AttrData.__init__(
    self,
    attrs
)
```

##### method: AttrData.dict

```py
AttrData.dict(
    self
)
```

##### method: AttrData.get

```py
AttrData.get(
    self,
    key
)
```


### class: AttrDataInt


### class: AttrDataStr


### class: FallbackAttrData

##### method: FallbackAttrData.__init__

```py
FallbackAttrData.__init__(
    self,
    *datas
)
```


##### function: wrap_attr_data

Wraps an object (hopefully) as a AttrBase item.

```py
wrap_attr_data(
    key,
    attr
)
```
