import pytest
from typing import TypedDict, Annotated, Optional, Any, List
from typing_extensions import NotRequired
from pytastic.core import Pytastic


@pytest.fixture
def vx():
    return Pytastic()


class SchemaWithStrip(TypedDict):
    _: Annotated[Any, "strip=True"]
    name: str
    age: int


class SchemaWithoutStrip(TypedDict):
    name: str
    age: int


class Inner(TypedDict):
    x: int


class Outer(TypedDict):
    _: Annotated[Any, "strip=True"]
    inner: Inner


class TestSchemaLevelStrip:
    def test_extra_keys_removed(self, vx):
        result = vx.validate(SchemaWithStrip, {"name": "Alice", "age": 30, "extra": "gone"})
        assert result == {"name": "Alice", "age": 30}
        assert "extra" not in result

    def test_no_extra_keys_unchanged(self, vx):
        result = vx.validate(SchemaWithStrip, {"name": "Bob", "age": 25})
        assert result == {"name": "Bob", "age": 25}

    def test_multiple_extra_keys_removed(self, vx):
        data = {"name": "C", "age": 1, "a": 1, "b": 2, "c": 3}
        result = vx.validate(SchemaWithStrip, data)
        assert result == {"name": "C", "age": 1}


class TestRuntimeStrip:
    def test_strip_true_removes_extra(self, vx):
        result = vx.validate(SchemaWithoutStrip, {"name": "A", "age": 10, "extra": "x"}, strip=True)
        assert result == {"name": "A", "age": 10}
        assert "extra" not in result

    def test_strip_false_preserves_extra(self, vx):
        result = vx.validate(SchemaWithoutStrip, {"name": "A", "age": 10, "extra": "x"}, strip=False)
        assert "extra" in result

    def test_strip_default_preserves_extra(self, vx):
        result = vx.validate(SchemaWithoutStrip, {"name": "A", "age": 10, "extra": "x"})
        assert "extra" in result


class TestNestedStrip:
    def test_runtime_strip_propagates_to_nested(self, vx):
        data = {"inner": {"x": 1, "extra_inner": "gone"}, "extra_outer": "gone"}
        result = vx.validate(Outer, data, strip=True)
        assert "extra_outer" not in result
        assert "extra_inner" not in result["inner"]

    def test_schema_strip_does_not_propagate_to_nested(self, vx):
        result = vx.validate(OuterWithStrip, {"inner": {"x": 1, "extra_inner": "stays"}, "extra_outer": "gone"})
        assert "extra_outer" not in result
        assert "extra_inner" in result["inner"]


class OuterWithStrip(TypedDict):
    _: Annotated[Any, "strip=True"]
    inner: Inner


class User(TypedDict):
    name: str


class OuterWithList(TypedDict):
    users: List[User]


class TestListStrip:
    def test_strip_propagates_into_list(self, vx):
        data = {"users": [{"name": "Alice", "extra": "gone"}, {"name": "Bob", "extra": "gone"}]}
        result = vx.validate(OuterWithList, data, strip=True)
        assert result == {"users": [{"name": "Alice"}, {"name": "Bob"}]}
