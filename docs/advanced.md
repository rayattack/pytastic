# Advanced Usage

## Dynamic Syntax
While standard validation uses `vx.validate(Schema, data)`, Pytastic offers a more concise, "dynamic" syntax for rapid development.

Once you register a schema, it becomes available as a method on the Pytastic instance.

```python
from pytastic import Pytastic
from typing import TypedDict

class User(TypedDict):
    name: str

vx = Pytastic()
vx.register(User)

# Standard
user = vx.validate(User, {"name": "Alice"})

# Dynamic (Cleaner!)
user = vx.User({"name": "Alice"})
```

This is particularly useful if you are using Pytastic as a minimal dependency-injection style validator in scripts.

## Nested Validation
Pytastic handles nested `TypedDict`s automatically. You don't need to manually validate sub-objects.

```python
class Address(TypedDict):
    street: str
    city: str
    zip: Annotated[str, "min_len=5"]

class User(TypedDict):
    username: str
    # Just reference the TypedDict class!
    address: Address

data = {
    "username": "tersoo",
    "address": {
        "street": "123 Python Way",
        "city": "Codeville",
        "zip": "90210"
    }
}

# helper will validate 'Address' recursively
vx.validate(User, data)
```

## How Pytastic Works (Code Generation)
Under the hood, Pytastic does **not** interpret your schema at runtime. That would be slow.

Instead, when you call `register` (or the first time you `validate`), Pytastic:
1.  Analyzes your `TypedDict` and `Annotated` hints.
2.  Generates optimal Python source code for a validation function (e.g., `def validate_User(...)`).
3.  Compiles this functions using `exec()` into memory.
4.  Caches it for future calls.

This "Just-In-Time" (JIT) compilation means Pytastic runs as fast as hand-written validation code, avoiding the overhead of traversing schema objects for every record.

### Viewing Generated Code
*(Internal Feature)*
If you are debugging, you can inspect the generated code by looking at the `codegen.py` compiler output, or by inspecting the compiled function wrapper. This is transparent to you as a user but explains why Pytastic benchmarks so effectively.
