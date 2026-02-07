import pytest
from typing import TypedDict, Annotated, List, NotRequired, Any
from pytastic.compiler import SchemaCompiler
from pytastic.exceptions import ValidationError
from pytastic.utils import parse_constraints

class TestAdvancedSyntax:
    def test_parser_conditionals(self):
        """Test parsing of 'condition ? constraint' syntax."""
        s = "payment_type==credit ? required"
        parsed = parse_constraints(s)
        # We expect a structured object or specific dict format
        # For now, let's assume it returns a list of constraint objects or a special dict
        # This test structure depends on the implementation of parse_constraints
        assert parsed

    def test_parser_logical_or(self):
        """Test parsing of 'A | B' syntax."""
        s = "format=email | regex=^[a-z]+$"
        parsed = parse_constraints(s)
        assert parsed

    def test_parser_negation(self):
        """Test parsing of '!constraint' syntax."""
        s = "!min_len=5"
        parsed = parse_constraints(s)
        assert parsed

    def test_conditional_validation(self):
        class Payment(TypedDict):
            payment_type: Annotated[str, "regex='^(credit|cash)$'"]
            card_number: Annotated[NotRequired[str], "payment_type==credit ? required"]

        compiler = SchemaCompiler()
        validator = compiler.compile(Payment)

        # Valid cases
        assert validator.validate({"payment_type": "cash"}) == {"payment_type": "cash"}
        assert validator.validate({"payment_type": "credit", "card_number": "1234"}) == {"payment_type": "credit", "card_number": "1234"}

        # Invalid: conditional required missing
        with pytest.raises(ValidationError) as exc:
            validator.validate({"payment_type": "credit"})
        assert "card_number" in str(exc.value)

    def test_logical_or_validation(self):
        class Contact(TypedDict):
            # Email OR numeric ID
            contact: Annotated[str, "format=email | regex=^[0-9]+$"]

        compiler = SchemaCompiler()
        validator = compiler.compile(Contact)

        assert validator.validate({"contact": "user@example.com"})
        assert validator.validate({"contact": "12345"})

        with pytest.raises(ValidationError):
            validator.validate({"contact": "invalid-contact"})

    def test_negation_validation(self):
        class Password(TypedDict):
            # Not 'password' AND min_len 1
            secret: Annotated[str, "!regex=^password$; min_len=1"]

        compiler = SchemaCompiler()
        validator = compiler.compile(Password)

        assert validator.validate({"secret": "secret123"})
        
        with pytest.raises(ValidationError):
            validator.validate({"secret": "password"})

    def test_array_contains(self):
        class User(TypedDict):
            tags: Annotated[List[str], "contains='regex=^admin$'"]
        
        compiler = SchemaCompiler()
        validator = compiler.compile(User)

        assert validator.validate({"tags": ["user", "admin"]})
        
        with pytest.raises(ValidationError):
            validator.validate({"tags": ["user", "guest"]})
