## pyinfra.api.facts


### class: FactBase

##### method: FactBase.process

```py
FactBase.process(
    self,
    output
)
```


### class: FactMeta

##### method: FactMeta.__init__

```py
FactMeta.__init__(
    cls,
    name,
    bases,
    attrs
)
```


##### function: get_fact

Wrapper around get_facts returning facts for one host or a function that does.

```py
get_fact(
    hostname,
    name,
    print_output=False
)
```


##### function: get_fact_names

```py
get_fact_names()
```


##### function: get_facts

```py
get_facts(
    name,
    arg=None,
    sudo=False,
    sudo_user=None,
    print_output=False
)
```


##### function: is_fact

```py
is_fact(
    name
)
```


##### function: set_print_facts

```py
set_print_facts(
    to_print
)
```
