# Pytastic

**No Magic. Just Python.**

Pytastic is a lightweight, dependency-free validation library that respects your standard Python type hints. It compiles `TypedDict` schemas into highly optimized Python code, making it strictly compliant and faster than many alternatives.

## Why Pytastic?

*   **Zero Dependencies**: Pure Python standard library only.
*   **Fast**: Uses compiled code generation to beat `pydantic`.
*   **Standard**: Uses `TypedDict` and `Annotated` from `typing`.
*   **Safe**: Strict validation options available.

## Performance

Benchmark results (100,000 validation iterations):

| Library | Time (s) | Ops/sec | Relative |
|---------|----------|---------|----------|
| msgspec | 0.053 | 1,877,872 | 1.00x |
| **Pytastic** | **0.179** | **557,277** | **3.37x** |
| Pydantic | 0.200 | 499,381 | 3.76x |

## Installation

```bash
pip install pytastic
```

## Quick Start
=== "Typed Syntax"
    ```python
    from pytastic import Pytastic
    from typing import TypedDict, Annotated, Literal

    vx = Pytastic()

    class User(TypedDict):
        username: Annotated[str, "min_len=3"]
        age: Annotated[int, "min=18"]
        role: Literal["admin", "user"]

    # Validate directly
    data = {"username": "tersoo", "age": 25, "role": "admin"}
    user = vx.validate(User, data)
    print(user)
    ```

=== "Dynamic Syntax"
    ```python
    vx.register(User)

    # Use as a method on vx
    user = vx.User({"username": "tersoo", "age": 25, "role": "admin"})
    ```
