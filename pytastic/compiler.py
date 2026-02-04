from abc import ABC, abstractmethod
from typing import Any, Type, Dict, get_origin, get_args, Union, List, Tuple, Annotated, _TypedDictMeta, Literal, cast, Generic, TypeVar, Set # type: ignore
from pytastic.validators import (
    Validator, NumberValidator, StringValidator, CollectionValidator, 
    UnionValidator, ObjectValidator, LiteralValidator, AnyValidator
)
from pytastic.exceptions import SchemaDefinitionError
from pytastic.utils import parse_constraints, normalize_key
from typing import get_type_hints, NotRequired, Required

class SchemaCompiler:
    """Compiles Python types (TypedDict, Annotated, etc.) into Validators."""
    
    def __init__(self):
        self._cache: Dict[Type, Validator] = {}

    def compile(self, schema: Type) -> Validator:
        """
        Compiles a schema type into a Validator instance.
        """
        if schema in self._cache: return self._cache[schema]
        validator = self._build_validator(schema)
        self._cache[schema] = validator
        return validator

    def _build_validator(self, schema: Type) -> Validator:
        origin = get_origin(schema)
        args = get_args(schema)

        if origin is Annotated:
            base_type = args[0]
            constraint_str = ""
            for arg in args[1:]:
                if isinstance(arg, str):
                    constraint_str += arg + ";"
            
            constraints = parse_constraints(constraint_str)
            base_origin = get_origin(base_type)
            
            if base_type is int or base_type is float:
                return NumberValidator(constraints, number_type=base_type)
            
            if base_type is str:
                return StringValidator(constraints)
            
            if base_origin is list or base_origin is List:
                 inner_type = get_args(base_type)[0] if get_args(base_type) else Any
                 item_validator = self.compile(inner_type)
                 return CollectionValidator(constraints, item_validator=item_validator)
                 
            if base_origin is tuple or base_origin is Tuple:
                # Annotated[tuple[int, str], "..."]
                inner_types = get_args(base_type)
                item_validators = [self.compile(t) for t in inner_types]
                return CollectionValidator(constraints, item_validator=item_validators)
            
            if base_origin is Union:
                union_mode = "one_of" if constraints.get("one_of") else "any_of"
                validators = [self.compile(t) for t in get_args(base_type)]
                return UnionValidator(validators, mode=union_mode)

            if self._is_typeddict(base_type):
                 return self._compile_typeddict(base_type, constraints)

            return self.compile(base_type)

        if self._is_typeddict(schema): return self._compile_typeddict(schema, {})
        if origin is list or origin is List:
             inner_type = args[0] if args else Any
             return CollectionValidator({}, item_validator=self.compile(inner_type))
        
        if origin is tuple or origin is Tuple:
            return CollectionValidator({}, item_validator=[self.compile(t) for t in args])
        if origin is Union:
            return UnionValidator([self.compile(t) for t in args], mode="any_of")
        if origin is Literal:
            return LiteralValidator(args)
        if schema is int or schema is float:
             return NumberValidator({}, number_type=schema)
        if schema is str:
             return StringValidator({})
        if schema is bool:
             return AnyValidator()
        if schema is Any:
             return AnyValidator()
        raise SchemaDefinitionError(f"Unsupported type: {schema}")

    def _is_typeddict(self, t: Type) -> bool:
        return isinstance(t, _TypedDictMeta) or (isinstance(t, type) and issubclass(t, dict) and hasattr(t, '__annotations__'))

    def _compile_typeddict(self, td_cls: Type, constraints: Dict[str, Any]) -> ObjectValidator:
        # Python 3.9+ get_type_hints(include_extras=True) includes Annotated
        type_hints = get_type_hints(td_cls, include_extras=True)
        fields = {}
        required_keys = set()
        is_total = getattr(td_cls, '__total__', True)
        
        for key, value in type_hints.items():
            is_required = is_total
            if hasattr(td_cls, '__required_keys__'): is_required = key in td_cls.__required_keys__
            if is_required: required_keys.add(key)
            fields[key] = self.compile(value)
            
        # Handle metadata from `_: Annotated[...]` pattern
        if '_' in fields:
             meta_annotation = td_cls.__annotations__.get('_', None)
             if meta_annotation and get_origin(meta_annotation) is Annotated:
                 args = get_args(meta_annotation)
                 constraint_str = ""
                 for arg in args[1:]:
                    if isinstance(arg, str):
                        constraint_str += arg + ";"
                 meta_constraints = parse_constraints(constraint_str)
                 constraints.update(meta_constraints)
             
             # Remove _ from fields and required keys checks
             fields.pop('_', None)
             required_keys.discard('_')
        return ObjectValidator(fields, constraints, required_keys)
