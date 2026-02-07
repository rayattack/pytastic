# Annotation Syntax

Pytastic uses `typing.Annotated` to define constraints. The syntax is a simple semi-colon separated string:

```python
Annotated[Type, "constraint1=value; constraint2=value; flag"]
```

## Numeric Constraints
Applies to `int` and `float`.

| Constraint | Aliases | Description | Example |
|------------|---------|-------------|---------|
| `min` | | Minimum value (inclusive) | `"min=0"` |
| `max` | | Maximum value (inclusive) | `"max=100"` |
| `exclusive_min` | | Minimum value (exclusive) | `"exclusive_min=0"` |
| `exclusive_max` | | Maximum value (exclusive) | `"exclusive_max=100"` |
| `step` | `multiple_of` | Value must be a multiple of this | `"step=0.5"` |

### Examples

=== "Age Validation"
    ```python
    class Person(TypedDict):
        # Must be 18 or older
        age: Annotated[int, "min=18"]
    ```

=== "Percentage"
    ```python
    class Stats(TypedDict):
        # 0.0 to 1.0
        score: Annotated[float, "min=0; max=1"]
    ```

=== "Step/Multiple"
    ```python
    class Product(TypedDict):
        # Must be customizable in 0.5kg increments
        weight: Annotated[float, "step=0.5"]
    ```

---

## String Constraints
Applies to `str`.

| Constraint | Aliases | Description | Example |
|------------|---------|-------------|---------|
| `min_len` | `min_length` | Minimum character length | `"min_len=3"` |
| `max_len` | `max_length` | Maximum character length | `"max_len=20"` |
| `regex` | `pattern` | Regular expression match | `"regex='^[a-z]+$'"` |
| `format` | | Pre-defined formats | `"format=email"` |

### Supported Formats

| Format | Description |
|--------|-------------|
| `email` | Basic email structure check (`@`) |
| `uuid` | UUID v4 format |
| `ipv4` | IPv4 address (e.g., `192.168.1.1`) |
| `date-time` | ISO8601 date-time (e.g., `2024-01-15T10:30:00`) |
| `uri` | URI format (e.g., `https://example.com`) |

### Examples

=== "Username"
    ```python
    class User(TypedDict):
        # Alphanumeric, 3-20 chars
        username: Annotated[str, "min_len=3; max_len=20; regex='^[a-zA-Z0-9_]+$'"]
    ```

=== "Email"
    ```python
    class Contact(TypedDict):
        email: Annotated[str, "format=email"]
    ```

=== "IPv4 Address"
    ```python
    class Server(TypedDict):
        ip: Annotated[str, "format=ipv4"]
    ```

=== "Timestamp"
    ```python
    class Event(TypedDict):
        created_at: Annotated[str, "format=date-time"]
    ```

---

## Collection Constraints
Applies to `List`, `list`, `Tuple`, or `tuple`.

| Constraint | Aliases | Description | Example |
|------------|---------|-------------|---------|
| `min_items` | | Minimum list length | `"min_items=1"` |
| `max_items` | | Maximum list length | `"max_items=5"` |
| `unique` | `unique_items` | All items must be unique | `"unique"` |
| `contains` | | At least one item must match | `"contains='regex=^admin$'"` |

### Examples

=== "Tags List"
    ```python
    class Post(TypedDict):
        # 1 to 5 unique tags
        tags: Annotated[List[str], "min_items=1; max_items=5; unique"]
    ```

=== "Contains Check"
    ```python
    class User(TypedDict):
        # Must have at least one 'admin' role
        roles: Annotated[List[str], "contains='regex=^admin$'"]
    ```

---

## Conditional Validation

Make validation rules depend on the values of other fields using the `condition ? constraint` syntax.

**Syntax:** `field==value ? constraint`

This is powerful for forms and APIs where field requirements change based on user input.

### Examples

=== "Conditional Required"
    ```python
    class Payment(TypedDict):
        payment_type: Annotated[str, "regex='^(credit|cash)$'"]
        # Card number is required ONLY if payment_type is 'credit'
        card_number: Annotated[NotRequired[str], "payment_type==credit ? required"]
    ```

=== "Conditional Constraint"
    ```python
    class User(TypedDict):
        user_type: str
        # Business users need longer usernames
        username: Annotated[str, "user_type==business ? min_len=10"]
    ```

=== "Object-Level Conditions"
    ```python
    class Order(TypedDict):
        # Use _ field for object-level rules
        _: Annotated[Any, "payment==credit ? card_number=required"]
        payment: str
        card_number: NotRequired[str]
    ```

---

## Logical Operators

Combine validation rules using `|` (OR) and `!` (NOT).

### OR (`|`)
Matches if *either* constraint passes.

```python
class Contact(TypedDict):
    # Field must be either an email OR a numeric ID
    contact_info: Annotated[str, "format=email | regex='^[0-9]+$'"]
```

### NOT (`!`)
Matches if the constraint *fails*.

```python
class Password(TypedDict):
    # Must NOT be exactly 'password'
    secret: Annotated[str, "!regex='^password$'; min_len=1"]
```

### Combined Example
```python
class Username(TypedDict):
    # Email OR alphanumeric, but NOT 'admin'
    name: Annotated[str, "format=email | regex='^[a-z0-9]+$'; !regex='^admin$'"]
```

> **Note:** When using regex patterns containing `|`, wrap them in single quotes to avoid conflicts with the OR operator: `"regex='^(a|b)$'"`.

---

## Tuple Constraints
Standard `Tuple` support works as expected for fixed-size arrays.

```python
class Point(TypedDict):
    # Exactly 2 floats: lat, lng
    lat_lng: Tuple[float, float]

class UserRecord(TypedDict):
    # Exact structure: (id, name, is_active)
    record: Tuple[int, str, bool]
```

---

## Object Constraints (Strict Mode)
Apply constraints to the `TypedDict` itself using a special `_` metadata field.

| Constraint | Aliases | Description | Example |
|------------|---------|-------------|---------|
| `strict` | | Disallow extra fields | `"strict"` |
| `min_props` | `min_properties` | Minimum number of present keys | `"min_props=2"` |

### Examples

=== "Strict User"
    ```python
    class User(TypedDict):
        # Rejects input with extra keys!
        _: Annotated[Any, "strict"]
        name: str
        age: int

    # Valid
    vx.validate(User, {"name": "A", "age": 1})

    # Invalid (raises ValidationError due to 'extra')
    vx.validate(User, {"name": "A", "age": 1, "extra": True})
    ```

---

## Union Types
Pytastic supports `Union` and `Optional` (which is `Union[T, None]`).

*   **AnyOf** (Default): Tries to match any type. Returns the first valid match.
*   **OneOf**: Ensures data matches *exactly one* type.

To specify `one_of`, enclose the Union in `Annotated`.

```python
class Search(TypedDict):
    # Can be a string OR a list of strings
    query: Union[str, List[str]]

class Exclusive(TypedDict):
    # Must be EITHER int OR float, but not both
    value: Annotated[Union[int, float], "one_of"]
```

## Literal Types
Ensures value is one of a specific set of constants.

```python
class Config(TypedDict):
    # Must be exactly "json" or "yaml"
    format: Literal["json", "yaml"]
    
    # Can also use numbers
    version: Literal[1, 2, 3]
```

## JSON Schema Metadata

You can also use `Annotated` to provide metadata for JSON Schema export (`title`, `description`, `default`). See [JSON Schema Export](json_schema.md) for details.

