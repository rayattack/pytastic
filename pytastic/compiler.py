from abc import ABC, abstractmethod
from typing import Any, Type, Dict, get_origin, get_args, Union, List, Tuple, Annotated, _TypedDictMeta, Literal, cast, Generic, TypeVar, Set # type: ignore
from pytastic.validators import (
    Validator, NumberValidator, StringValidator, CollectionValidator, 
    UnionValidator, ObjectValidator, LiteralValidator, AnyValidator,
    ConditionalValidator, OrValidator, NotValidator
)
from pytastic.exceptions import SchemaDefinitionError
from pytastic.utils import parse_constraints, ConstraintNode, LeafConstraint, ConditionalConstraint, OrConstraint, NotConstraint, normalize_key

try:
    from typing import NotRequired, Required, get_type_hints
except ImportError:
    try:
        from typing_extensions import NotRequired, Required, get_type_hints
    except ImportError:
        NotRequired = Required = object() # Fallback
        from typing import get_type_hints

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
            
            parsed = parse_constraints(constraint_str)
            base_origin = get_origin(base_type)
            base_validator = None
            
            if isinstance(parsed, dict):
                constraints = parsed
                wrappers = []
            else:
                
                constraints = {}
                wrappers = []
                
                for node in parsed:
                    if isinstance(node, LeafConstraint):
                        constraints[node.key] = node.value
                    else:
                        wrappers.append(node)
            if base_type is int or base_type is float:
                base_validator = NumberValidator(constraints, number_type=base_type)
            elif base_type is str:
                base_validator = StringValidator(constraints)
            elif base_origin is list or base_origin is List:
                 inner_type = get_args(base_type)[0] if get_args(base_type) else Any
                 item_validator = self.compile(inner_type)
                 contains_validator = None
                 if 'contains' in constraints:
                     contains_validator = self.compile(Annotated[inner_type, constraints['contains']])

                 base_validator = CollectionValidator(constraints, item_validator=item_validator, contains_validator=contains_validator)
                 
            elif base_origin is tuple or base_origin is Tuple:
                inner_types = get_args(base_type)
                item_validators = [self.compile(t) for t in inner_types]
                base_validator = CollectionValidator(constraints, item_validator=item_validators)
            
            elif base_origin is Union:
                union_mode = "one_of" if constraints.get("one_of") else "any_of"
                validators = [self.compile(t) for t in get_args(base_type)]
                base_validator = UnionValidator(validators, mode=union_mode, metadata=constraints)

            elif base_origin is Literal:
                base_validator = LiteralValidator(get_args(base_type), metadata=constraints)

            elif self._is_typeddict(base_type):
                 base_validator = self._compile_typeddict(base_type, constraints)

            else:
                 base_validator = self.compile(base_type)

            if wrappers:
                return self._build_complex_validator(wrappers, base_type, base_validator)
            
            return base_validator

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
            
        if origin is NotRequired or origin is Required:
             return self.compile(args[0])

        if schema is int or schema is float:
             return NumberValidator({}, number_type=schema)
        if schema is str:
             return StringValidator({})
        if schema is bool:
             return AnyValidator()
        if schema is Any:
             return AnyValidator()
        if schema is type(None):
             return LiteralValidator((None,))
        
        return AnyValidator()

    def _build_complex_validator(self, nodes: List[ConstraintNode], base_type: Type, base_validator: Validator) -> Validator:
        """Combines a base validator with structural constraints (AND logic)."""
        validators = [base_validator]
        for node in nodes:
            validators.append(self._node_to_validator(node, base_type))
        return CompositeValidator(validators)

    def _node_to_validator(self, node: ConstraintNode, base_type: Type) -> Validator:
        """Converts a ConstraintNode into a Validator for the given base_type."""
        if isinstance(node, LeafConstraint):
            return self.compile(Annotated[base_type, f"{node.key}={node.value}"])
            
        if isinstance(node, ConditionalConstraint):
            return ConditionalValidator(node.condition, self._node_to_validator(node.constraint, base_type))
            
        if isinstance(node, NotConstraint):
            sub = self._node_to_validator(node.constraint, base_type)
            return NotValidator(sub)
            
        if isinstance(node, OrConstraint):
            return OrValidator([self._node_to_validator(n, base_type) for n in node.constraints])
            
        return AnyValidator()

    def _is_typeddict(self, t: Type) -> bool:
        return isinstance(t, _TypedDictMeta) or (isinstance(t, type) and issubclass(t, dict) and hasattr(t, '__annotations__'))

    def _compile_typeddict(self, td_cls: Type, constraints: Dict[str, Any]) -> ObjectValidator:
        type_hints = get_type_hints(td_cls, include_extras=True)
        fields = {}
        required_keys = set()
        conditional_required = []
        is_total = getattr(td_cls, '__total__', True)
        
        if '_' in type_hints:
             meta_annotation = type_hints['_']
             if get_origin(meta_annotation) is Annotated:
                 args = get_args(meta_annotation)
                 constraint_str = ""
                 for arg in args[1:]:
                    if isinstance(arg, str):
                        constraint_str += arg + ";"
                 
                 parsed = parse_constraints(constraint_str)
                 if isinstance(parsed, dict):
                     constraints.update(parsed)
                 else:
                     for node in parsed:
                         if isinstance(node, ConditionalConstraint):
                             if isinstance(node.constraint, LeafConstraint) and node.constraint.value == 'required':
                                 conditional_required.append((node.condition, node.constraint.key))
                         elif isinstance(node, LeafConstraint):
                              constraints[node.key] = node.value

        for key, value in type_hints.items():
            if key == '_': continue
            
            is_required = is_total
            if hasattr(td_cls, '__required_keys__'): is_required = key in td_cls.__required_keys__
            
            if get_origin(value) is Annotated:
                args = get_args(value)
                c_str = ""
                for arg in args[1:]:
                    if isinstance(arg, str) and 'required' in arg:
                        c_str += arg + ";"
                
                if c_str:
                    f_parsed = parse_constraints(c_str)
                    if not isinstance(f_parsed, dict):
                        for node in f_parsed:
                            if isinstance(node, ConditionalConstraint) and isinstance(node.constraint, LeafConstraint):
                                if node.constraint.key == 'required':
                                     conditional_required.append((node.condition, key))

            if is_required: required_keys.add(key)
            fields[key] = self.compile(value)
            
        return ObjectValidator(fields, constraints, required_keys, conditional_required)

class CompositeValidator(Validator[Any]):
    """Applies multiple validators (AND logic)."""
    def __init__(self, validators: List[Validator]):
        super().__init__()
        self.validators = validators
        
    def validate(self, data: Any, path: str = "", context: Any = None) -> Any:
        val = data
        for v in self.validators:
            val = v.validate(val, path, context)
        return val
