# JSON Schema Export

Pytastic bridges the gap between Python types and standard JSON Schema. You can export any Pytastic-compatible `TypedDict` to a JSON Schema string, perfect for sharing with frontends (React, Vue) or other services.

## Basic Export

Use the `vx.schema()` method.

```python
import json
from pytastic import Pytastic
from typing import TypedDict, Annotated

class Product(TypedDict):
    id: Annotated[int, "min=1"]
    name: Annotated[str, "min_len=3"]
    tags: Annotated[List[str], "unique"]

vx = Pytastic()

# Get schema as a JSON string
schema_json = vx.schema(Product)
print(schema_json)
```

### Output
```json
{
  "type": "object",
  "properties": {
    "id": {
      "type": "integer",
      "minimum": 1.0
    },
    "name": {
      "type": "string",
      "minLength": 3
    },
    "tags": {
      "type": "array",
      "uniqueItems": true,
      "items": {
        "type": "string"
      }
    }
  },
  "required": [
    "id",
    "name",
    "tags"
  ],
  "additionalProperties": true
}
```

## Features Supported
The schema generator respects all Pytastic constraints:

*   **Numbers**: `minimum`, `maximum`, `multipleOf`.
*   **Strings**: `minLength`, `maxLength`, `pattern`, `format`.
*   **Collections**: `minItems`, `maxItems`, `uniqueItems`.
*   **Tuples**: Generates `prefixItems` (JSON Schema 2020-12) for position-dependent validation.
*   **Unions**: Generates `oneOf` or `anyOf`.
*   **Literals**: Generates `enum` (and `type: null` for `None`).

## Metadata (`title`, `description`, `default`)

You can add standard JSON Schema metadata using `Annotated`. Pytastic extracts these fields and injects them into the schema.

```python
from typing import Annotated, TypedDict
from pytastic import Pytastic

class Config(TypedDict):
    api_key: Annotated[str, "description='Your API Key'; title='API Key'"]
    retries: Annotated[int, "default=5; description='Number of retries'"]

vx = Pytastic()
schema = vx.schema(Config)
# {
#   "type": "object",
#   "properties": {
#     "api_key": { "type": "string", "title": "API Key", "description": "Your API Key" },
#     "retries": { "type": "integer", "default": 5, "description": "Number of retries" }
#   },
#   ...
# }
```

## Optional and Required Fields

- **Required**: By default, all fields in a `TypedDict` are required.
- **Optional (`NotRequired`)**: Use `typing.NotRequired` (or `total=False`) to make fields optional in the schema (removed from `required` list).
- **Nullable (`Optional`)**: Use `typing.Optional[T]` to allow `null` values (`anyOf: [{type: T}, {type: "null"}]`).

```python
try:
    from typing import NotRequired # Python 3.11+
except ImportError:
    from typing_extensions import NotRequired

class User(TypedDict):
    id: int                     # Required, integer
    name: NotRequired[str]      # Optional property, string
    bio: Optional[str]          # Required property, string OR null
```

## Usage in APIs
You can serve this schema directly from your API endpoints so clients know exactly what data format to send.

```python
# Flask example
@app.route("/schema/product")
def get_product_schema():
    return vx.schema(Product), 200, {'Content-Type': 'application/json'}
```
