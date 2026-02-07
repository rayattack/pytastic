# Pytastic

**No Magic. Just Python.**

Pytastic is a lightweight validation layer that respects your standard Python type hints. If you know `TypedDict` and `Annotated`, you already know how to use Pytastic.

View Docs at [Pytastic Documentation](https://rayattack.github.io/pytastic/)

## Why?
- **Zero Dependencies**: Pure Python standard library.
- **No Learning Curve**: It's just standard Python typing.
- **IDE Friendly**: We use standard types, so your IDE autocompletion works out of the box.
- **Fast**: Code generation makes Pytastic faster than Pydantic for common use cases.

## Performance

Benchmark results (100,000 validation iterations):

| Library | Time (s) | Ops/sec | Relative |
|---------|----------|---------|----------|
| msgspec | 0.0533 | 1,877,872 | 1.00x |
| **Pytastic** | **0.1794** | **557,277** | **3.37x** |
| Pydantic | 0.2002 | 499,381 | 3.76x |

**Pytastic is faster than Pydantic** i.e. Pure Python with zero dependencies!

## Installation

```bash
pip install pytastic
```

## Usage

```python
from pytastic import Pytastic
from typing import TypedDict, Annotated, List, Literal

vx = Pytastic()

# 1. Define Schema
class User(TypedDict):
    username: Annotated[str, "min_len=3; regex=^[a-z_]+$"]
    age: Annotated[int, "min=18"]
    role: Literal["admin", "user"]
```

# 2. Usage Patterns

## Option A: Typed (Recommended)
**No registration required.** Best for IDE autocompletion.
```python
try:
    user = vx.validate(User, {"username": "tersoo", "age": 25, "role": "admin"})
    print(user)
except Exception as e:
    print(e)
```

## Option B: Dynamic (Requires Registration)
**Registration required.** Best for quick scripts or cleaner syntax.
```python
vx.register(User)

# Now you can use the class name directly on the validator instance
user = vx.User({"username": "tersoo", "age": 25, "role": "admin"})
```

## 3. JSON Schema
```python
# Export standard JSON Schema
print(vx.schema(User))
# Output:
# {
#   "type": "object",
#   "properties": {
#     "username": { "type": "string", "minLength": 3 ... },
#     ...
#   }
# }
```

## License

MIT
