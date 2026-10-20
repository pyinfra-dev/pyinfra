# Operations

Operations either describe an end state for hosts in the inventory (declarative — pyinfra checks current state and only acts if the host differs) or execute specific commands directly (imperative — runs every time). Most operations are declarative; see [Using Operations](using-operations.md) for the difference. All operations accept a set of [global arguments](arguments.md) and are grouped as Python modules.

**Want a new operation?** Check out [the writing operations guide](api/operations.md).

--8<-- "operations-cards.html"
