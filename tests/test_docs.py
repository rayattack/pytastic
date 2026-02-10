from typing import TypedDict, Annotated, List, Literal, Union
from pytastic import Pytastic
from pytastic.exceptions import ValidationError

class Review(TypedDict):
    rating: Annotated[int, "min=1; max=5"]
    comment: Annotated[str, "max_len=500"]

class Product(TypedDict):
    # UUID format valid: 123e4567-e89b-12d3-a456-426614174000
    id: Annotated[str, "format=uuid"]
    name: Annotated[str, "min_len=3"]
    tags: Annotated[List[str], "unique=True; min_items=1"]
    reviews: List[Review]
    stock: Annotated[int, "min=0"]
    status: Literal["in_stock", "out_of_stock"]

pc = Pytastic()

# Validate
data = {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Super Widget",
    "tags": ["gadget", "widget"],
    "reviews": [{"rating": 5, "comment": "Great!"}],
    "stock": 10,
    "status": "in_stock"
}

try:
    pc.validate(Product, data)
    print("Validation passed!")
except ValidationError as e:
    print(f"Validation failed: {e}")

# Generate Schema
print("--- JSON Schema ---")
print(pc.schema(Product))
