from typing import TypedDict, Annotated, List
from pytastic import Pytastic, ValidationError
import pytest

vx = Pytastic()

class Address(TypedDict):
    city: str
    zip: Annotated[str, "min_len=5"]

class User(TypedDict):
    name: Annotated[str, "min_len=2"]
    age: int
    address: Address

def test_partial_true_legacy():
    # partial=True makes everything optional
    data = {}
    vx.validate(User, data, partial=True)

def test_partial_list_top_level():
    # partial=['age'] makes age optional, but name required
    
    # Case 1: Missing age is OK
    data = {"name": "Alice", "address": {"city": "NY", "zip": "12345"}}
    vx.validate(User, data, partial=["age"])

    # Case 2: Missing name raises Error
    data_missing_name = {"age": 25, "address": {"city": "NY", "zip": "12345"}}
    with pytest.raises(ValidationError) as exc:
        vx.validate(User, data_missing_name, partial=["age"])
    assert "name" in str(exc.value)

def test_partial_nested_list():
    # partial=['address.zip'] makes zip optional, but city required
    
    # Case 1: Missing zip is OK
    data = {"name": "Alice", "age": 25, "address": {"city": "NY"}}
    vx.validate(User, data, partial=["address.zip"])

    # Case 2: Missing city raises Error
    data_missing_city = {"name": "Alice", "age": 25, "address": {"zip": "12345"}}
    with pytest.raises(ValidationError) as exc:
        vx.validate(User, data_missing_city, partial=["address.zip"])
    assert "city" in str(exc.value)

def test_partial_mixed():
    # partial=['age', 'address.zip']
    data = {"name": "Alice", "address": {"city": "NY"}}
    vx.validate(User, data, partial=["age", "address.zip"])

def test_partial_invalid_keys_ignored():
    # partial=['invalid', 'age'] -> 'age' works, 'invalid' ignored
    data = {"name": "Alice", "address": {"city": "NY", "zip": "12345"}}
    vx.validate(User, data, partial=["age", "invalid"])

def test_partial_false_regression():
    # partial=False (default) -> everything required
    with pytest.raises(ValidationError):
        vx.validate(User, {"name": "Alice"}) # Missing age/address
