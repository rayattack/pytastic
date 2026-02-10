import pytest
from typing import TypedDict, Annotated, Optional, Any
from typing_extensions import NotRequired
from pytastic.core import Pytastic


@pytest.fixture
def vx():
    return Pytastic()


class User(TypedDict):
    name: str
    email: str
    username: str
    age: int


class TestPartialValidation:
    def test_partial_allows_subset(self, vx):
        result = vx.validate(User, {"name": "Alice", "email": "a@b.com"}, partial=True)
        assert result == {"name": "Alice", "email": "a@b.com"}

    def test_partial_validates_present_types(self, vx):
        from pytastic.exceptions import ValidationError
        with pytest.raises(ValidationError):
            vx.validate(User, {"name": 123}, partial=True)

    def test_partial_empty_dict(self, vx):
        result = vx.validate(User, {}, partial=True)
        assert result == {}

    def test_partial_false_enforces_required(self, vx):
        from pytastic.exceptions import ValidationError
        with pytest.raises(ValidationError):
            vx.validate(User, {"name": "Alice"})

    def test_partial_does_not_fill_defaults(self, vx):
        result = vx.validate(User, {"name": "Alice"}, partial=True)
        assert "email" not in result
        assert "username" not in result
        assert "age" not in result


class TestPartialWithStrip:
    def test_partial_and_strip_combined(self, vx):
        data = {"name": "Alice", "email": "a@b.com", "extra": "gone"}
        result = vx.validate(User, data, partial=True, strip=True)
        assert result == {"name": "Alice", "email": "a@b.com"}
        assert "extra" not in result
        assert "username" not in result
